"""Tabular dataset parser supporting robust CSV, TSV, Parquet, and Excel processing."""

import csv
import io
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO, List, Optional
import chardet
import openpyxl
import pandas as pd
import pyarrow.parquet as pq

logger = logging.getLogger("agentiq.storage.parser")


class DatasetParseError(Exception):
    """Base exception for parsing failures."""
    pass


class EmptyDatasetError(DatasetParseError):
    """Raised when uploaded file contains no rows or data."""
    pass


@dataclass
class DatasetMetadata:
    """Introspected dataset structure and encoding metadata."""
    row_count: int
    column_count: int
    columns: List[str]
    original_columns: List[str]
    sheet_names: List[str] = field(default_factory=list)
    active_sheet: Optional[str] = None
    detected_encoding: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    sample_preview: List[dict] = field(default_factory=list)


def deduplicate_headers(headers: List[str]) -> tuple[List[str], List[str]]:
    """Deterministically deduplicate header names (col, col_1, col_2...).
    
    Returns:
        (clean_headers, warnings)
    """
    counts: dict[str, int] = {}
    clean: List[str] = []
    warnings: List[str] = []

    for idx, raw_h in enumerate(headers):
        name = str(raw_h).strip() if raw_h is not None else f"unnamed_{idx}"
        if not name:
            name = f"unnamed_{idx}"

        if name not in counts:
            counts[name] = 1
            clean.append(name)
        else:
            new_name = f"{name}_{counts[name]}"
            counts[name] += 1
            clean.append(new_name)
            warnings.append(f"Duplicate header '{name}' at index {idx} renamed to '{new_name}'")

    return clean, warnings


class DatasetParser:
    """High-performance parser for extracting dimensions and schema from tabular files."""

    SUPPORTED_ENCODINGS = ["utf-8", "utf-8-sig", "cp1252", "latin-1"]

    @classmethod
    def detect_encoding(cls, stream_or_path: BinaryIO | Path, sample_size: int = 65536) -> str:
        """Detect text encoding with ordered fallbacks: UTF-8 -> UTF-8-BOM -> Chardet -> CP1252 -> Latin-1."""
        if isinstance(stream_or_path, Path):
            with open(stream_or_path, "rb") as f:
                sample = f.read(sample_size)
        else:
            pos = stream_or_path.tell()
            sample = stream_or_path.read(sample_size)
            stream_or_path.seek(pos)

        if not sample:
            return "utf-8"

        # 1. Check UTF-8 BOM
        if sample.startswith(b"\xef\xbb\xbf"):
            return "utf-8-sig"

        # 2. Try clean strict UTF-8
        try:
            sample.decode("utf-8")
            return "utf-8"
        except UnicodeDecodeError:
            pass

        # 3. Try automatic detection with chardet
        detected = chardet.detect(sample)
        if detected and detected.get("encoding") and (detected.get("confidence") or 0) > 0.7:
            enc = detected["encoding"].lower()
            try:
                sample.decode(enc)
                return enc
            except (UnicodeDecodeError, LookupError):
                pass

        # 4. Fallback to CP1252
        try:
            sample.decode("cp1252")
            return "cp1252"
        except UnicodeDecodeError:
            pass

        # 5. Universal byte fallback: Latin-1
        return "latin-1"

    @classmethod
    def parse_csv(
        cls,
        file_path_or_stream: Path | BinaryIO,
        delimiter: Optional[str] = None,
    ) -> DatasetMetadata:
        """Parse CSV/TSV file handling encoding fallbacks, empty files, and duplicate headers."""
        # 1. Pre-check empty content
        if isinstance(file_path_or_stream, Path):
            if not file_path_or_stream.is_file() or file_path_or_stream.stat().st_size == 0:
                raise EmptyDatasetError("The uploaded CSV file is empty (0 bytes).")
        else:
            pos = file_path_or_stream.tell()
            first_byte = file_path_or_stream.read(1)
            file_path_or_stream.seek(pos)
            if not first_byte:
                raise EmptyDatasetError("The uploaded CSV file is empty (0 bytes).")

        encoding = cls.detect_encoding(file_path_or_stream)
        warnings: List[str] = []

        # 2. Read raw header line to capture true original duplicates before Pandas auto-mangles them
        if isinstance(file_path_or_stream, Path):
            file_obj = open(file_path_or_stream, "r", encoding=encoding, errors="replace", newline="")
            should_close = True
        else:
            file_path_or_stream.seek(0)
            file_obj = io.TextIOWrapper(file_path_or_stream, encoding=encoding, errors="replace", newline="")
            should_close = False

        try:
            reader = csv.reader(file_obj, delimiter=delimiter or ",")
            try:
                raw_headers = next(reader)
            except StopIteration:
                raise EmptyDatasetError("The uploaded CSV file is empty and contains no headers.")
            except Exception as e:
                # Try sniffing separator if comma failed
                file_obj.seek(0)
                try:
                    sample_line = file_obj.readline()
                    dialect = csv.Sniffer().sniff(sample_line)
                    file_obj.seek(0)
                    reader = csv.reader(file_obj, dialect)
                    raw_headers = next(reader)
                except Exception:
                    raise DatasetParseError(f"Could not parse CSV headers: {e}")

            if not raw_headers:
                raise EmptyDatasetError("The uploaded CSV file contains no column headers.")

            # Explicitly strip UTF-8 BOM characters (\ufeff) from header strings
            raw_headers = [str(h).lstrip("\ufeff").strip() for h in raw_headers]

            clean_headers, dup_warnings = deduplicate_headers(raw_headers)
            warnings.extend(dup_warnings)

            # Count rows
            row_count = 0
            for _ in reader:
                row_count += 1

            if row_count == 0:
                raise EmptyDatasetError("The uploaded CSV file contains headers but 0 data rows.")

        finally:
            if should_close:
                file_obj.close()
            else:
                file_obj.detach()

        # 3. Read preview using deduplicated clean headers
        if isinstance(file_path_or_stream, Path):
            stream_target = file_path_or_stream
        else:
            file_path_or_stream.seek(0)
            stream_target = file_path_or_stream

        try:
            df = pd.read_csv(
                stream_target,
                encoding=encoding,
                sep=delimiter or None,
                engine="python",
                names=clean_headers,
                header=0,
                nrows=5,
            )
            preview = df.to_dict(orient="records")
        except Exception as read_err:
            logger.debug(f"Preview extraction fallback: {read_err}")
            preview = []

        return DatasetMetadata(
            row_count=row_count,
            column_count=len(clean_headers),
            columns=clean_headers,
            original_columns=raw_headers,
            sheet_names=[],
            active_sheet=None,
            detected_encoding=encoding,
            warnings=warnings,
            sample_preview=preview,
        )

    @classmethod
    def parse_excel(
        cls,
        file_path_or_stream: Path | BinaryIO,
        sheet_name: Optional[str] = None,
    ) -> DatasetMetadata:
        """Parse Excel workbook with openpyxl in read-only mode to prevent memory exhaustion."""
        try:
            wb = openpyxl.load_workbook(file_path_or_stream, read_only=True, data_only=True)
            sheet_names = wb.sheetnames
        except Exception as e:
            raise DatasetParseError(f"Invalid Excel workbook: {e}") from e

        if not sheet_names:
            raise EmptyDatasetError("The uploaded Excel workbook contains no worksheets.")

        target_sheet_name = sheet_name or sheet_names[0]
        if target_sheet_name not in sheet_names:
            target_sheet_name = sheet_names[0]

        ws = wb[target_sheet_name]
        warnings: List[str] = []

        row_iter = ws.iter_rows(values_only=True)
        try:
            first_row = next(row_iter)
        except StopIteration:
            raise EmptyDatasetError(f"Worksheet '{target_sheet_name}' is empty.")

        while first_row is not None and all(v is None for v in first_row):
            try:
                first_row = next(row_iter)
            except StopIteration:
                raise EmptyDatasetError(f"Worksheet '{target_sheet_name}' contains no header row.")

        raw_headers = [str(cell) if cell is not None else f"unnamed_{i}" for i, cell in enumerate(first_row)]
        clean_headers, dup_warnings = deduplicate_headers(raw_headers)
        warnings.extend(dup_warnings)

        row_count = 0
        sample_rows: List[dict] = []
        for r in row_iter:
            if any(cell is not None for cell in r):
                row_count += 1
                if len(sample_rows) < 5:
                    sample_dict = {
                        clean_headers[i]: r[i] if i < len(r) else None
                        for i in range(len(clean_headers))
                    }
                    sample_rows.append(sample_dict)

        wb.close()

        if row_count == 0:
            raise EmptyDatasetError(f"Worksheet '{target_sheet_name}' contains headers but 0 data rows.")

        return DatasetMetadata(
            row_count=row_count,
            column_count=len(clean_headers),
            columns=clean_headers,
            original_columns=raw_headers,
            sheet_names=sheet_names,
            active_sheet=target_sheet_name,
            detected_encoding="excel/binary",
            warnings=warnings,
            sample_preview=sample_rows,
        )

    @classmethod
    def parse_parquet(cls, file_path_or_stream: Path | BinaryIO) -> DatasetMetadata:
        """Parse Apache Parquet dataset using PyArrow."""
        try:
            parquet_file = pq.ParquetFile(file_path_or_stream)
            schema = parquet_file.schema_arrow
            metadata = parquet_file.metadata
        except Exception as e:
            raise DatasetParseError(f"Invalid Parquet file: {e}") from e

        raw_headers = [field.name for field in schema]
        clean_headers, warnings = deduplicate_headers(raw_headers)

        row_count = metadata.num_rows
        if row_count == 0:
            raise EmptyDatasetError("The uploaded Parquet dataset has 0 rows.")

        preview: List[dict] = []
        try:
            first_batch = parquet_file.read_row_group(0)
            preview = first_batch.slice(0, 5).to_pylist()
        except Exception as preview_err:
            logger.debug(f"Could not load parquet preview: {preview_err}")

        return DatasetMetadata(
            row_count=row_count,
            column_count=len(clean_headers),
            columns=clean_headers,
            original_columns=raw_headers,
            sheet_names=[],
            active_sheet=None,
            detected_encoding="parquet/snappy",
            warnings=warnings,
            sample_preview=preview,
        )

    @classmethod
    def introspect_dataset(
        cls,
        file_path_or_stream: Path | BinaryIO,
        filename: str,
    ) -> DatasetMetadata:
        """Dispatch introspection based on file extension."""
        ext = Path(filename).suffix.lower()
        if ext in (".csv", ".tsv", ".txt"):
            return cls.parse_csv(file_path_or_stream, delimiter="\t" if ext == ".tsv" else None)
        elif ext in (".xlsx", ".xlsm", ".xltx", ".xltm"):
            return cls.parse_excel(file_path_or_stream)
        elif ext in (".parquet", ".pq"):
            return cls.parse_parquet(file_path_or_stream)
        else:
            raise DatasetParseError(f"Unsupported file format '{ext}' for introspection.")
