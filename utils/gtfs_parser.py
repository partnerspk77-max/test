"""
Defensive GTFS Archive Parser.
Reads zip archives in-memory and parses CSV files with automatic UTF-8 BOM stripping
and safe column access to prevent crashes if column names or formats shift.
"""

import io
import csv
import zipfile
import logging

logger = logging.getLogger("etl_worker")


def extract_gtfs_archive(zip_bytes):
    """
    Extracts all text CSV files from an in-memory GTFS zip archive into a dictionary of file contents.
    Returns: dict of {filename: text_content}
    """
    files = {}
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            for name in z.namelist():
                # Process only genuine CSV/text files (skip __MACOSX resource forks and hidden files)
                if ("__MACOSX" in name) or name.split("/")[-1].startswith("."):
                    continue
                if name.endswith(".txt") or name.endswith(".csv"):
                    base_name = name.split("/")[-1]
                    try:
                        raw_data = z.read(name)
                        # utf-8-sig automatically strips UTF-8 BOM markers (\ufeff)
                        text = raw_data.decode("utf-8-sig")
                        files[base_name] = text
                    except Exception as e:
                        logger.warning("Failed to decode entry %s in GTFS archive: %s", name, e)
    except zipfile.BadZipFile as e:
        logger.error("Corrupted or invalid zip file supplied to GTFS parser: %s", e)
        raise

    logger.info("Successfully extracted %d GTFS tables from archive: %s", len(files), list(files.keys()))
    return files


def parse_csv_table(csv_text):
    """
    Safely parses CSV text into a list of row dictionaries.
    Uses defensive column trimming and strips empty trailing lines.
    """
    if not csv_text or not csv_text.strip():
        return []

    stream = io.StringIO(csv_text.strip())
    reader = csv.DictReader(stream)

    # Normalize column names: strip whitespace and BOM artifacts
    clean_fieldnames = [f.strip() if f else "" for f in (reader.fieldnames or [])]
    reader.fieldnames = clean_fieldnames

    rows = []
    for row in reader:
        # Strip string values and drop None keys
        clean_row = {
            k: (v.strip() if isinstance(v, str) else v)
            for k, v in row.items()
            if k
        }
        rows.append(clean_row)

    return rows
