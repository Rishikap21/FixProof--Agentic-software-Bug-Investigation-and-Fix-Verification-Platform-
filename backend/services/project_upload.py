
import os
import shutil
import stat
import tempfile
import zipfile

from pathlib import Path, PurePosixPath

UPLOAD_DIR = Path(__file__).resolve().parents[1] / "uploads"

MAX_UPLOAD_SIZE = 50 * 1024 * 1024       # 50 MB
MAX_EXTRACTED_SIZE = 200 * 1024 * 1024   # 200 MB
MAX_FILES = 1000

CHUNK_SIZE = 1024 * 1024


class ProjectUploadError(Exception):
    pass


def extract_project(upload_file):
    """
    Save and safely extract a ZIP archive.

    Returns the absolute path of the extracted project directory.
    """

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    temp_path = None
    project_dir = None

    try:
        # Save the uploaded archive with a temporary filename.
        with tempfile.NamedTemporaryFile(
            mode="wb",
            suffix=".zip",
            dir=UPLOAD_DIR,
            delete=False
        ) as temp_file:

            temp_path = Path(temp_file.name)
            total_upload_size = 0

            while True:
                chunk = upload_file.file.read(CHUNK_SIZE)

                if not chunk:
                    break

                total_upload_size += len(chunk)

                if total_upload_size > MAX_UPLOAD_SIZE:
                    raise ProjectUploadError(
                        "ZIP upload exceeds the 50 MB limit."
                    )

                temp_file.write(chunk)

        if total_upload_size == 0:
            raise ProjectUploadError("Uploaded ZIP file is empty.")

        # Validate ZIP archive.
        if not zipfile.is_zipfile(temp_path):
            raise ProjectUploadError("Uploaded file is not a valid ZIP archive.")

        project_dir = Path(
            tempfile.mkdtemp(prefix="project_", dir=UPLOAD_DIR)
        )

        extracted_total = 0
        file_count = 0

        with zipfile.ZipFile(temp_path, "r") as archive:

            entries = archive.infolist()

            if not entries:
                raise ProjectUploadError("ZIP archive is empty.")

            if len(entries) > MAX_FILES:
                raise ProjectUploadError(
                    "ZIP contains too many files."
                )

            for entry in entries:

                original_name = entry.filename

                # Reject Windows separators and absolute paths.
                if "\\" in original_name or original_name.startswith("/"):
                    raise ProjectUploadError(
                        "ZIP contains an unsafe file path."
                    )

                relative_path = PurePosixPath(original_name)

                if (
                    relative_path.is_absolute()
                    or ".." in relative_path.parts
                    or ":" in original_name
                ):
                    raise ProjectUploadError(
                        "ZIP contains an unsafe file path."
                    )

                if not relative_path.parts:
                    raise ProjectUploadError(
                        "ZIP contains an invalid file path."
                    )

                # Reject symbolic links.
                unix_mode = entry.external_attr >> 16

                if stat.S_ISLNK(unix_mode):
                    raise ProjectUploadError(
                        "ZIP contains a symbolic link."
                    )

                destination = project_dir.joinpath(
                    *relative_path.parts
                ).resolve()

                if not destination.is_relative_to(project_dir.resolve()):
                    raise ProjectUploadError(
                        "ZIP contains a path outside the project directory."
                    )

                if entry.is_dir():
                    destination.mkdir(parents=True, exist_ok=True)
                    continue

                file_count += 1

                if file_count > MAX_FILES:
                    raise ProjectUploadError(
                        "ZIP contains too many files."
                    )

                extracted_total += entry.file_size

                if extracted_total > MAX_EXTRACTED_SIZE:
                    raise ProjectUploadError(
                        "Extracted project exceeds the 200 MB limit."
                    )

                destination.parent.mkdir(
                    parents=True,
                    exist_ok=True
                )

                # Stream extraction rather than loading entire files into memory.
                with archive.open(entry, "r") as source:
                    with open(destination, "xb") as target:
                        shutil.copyfileobj(
                            source,
                            target,
                            length=CHUNK_SIZE
                        )

        if file_count == 0:
            raise ProjectUploadError(
                "ZIP archive does not contain any files."
            )

        return str(project_dir.resolve())

    except ProjectUploadError:
        if project_dir and project_dir.exists():
            shutil.rmtree(project_dir, ignore_errors=True)
        raise

    except (zipfile.BadZipFile, RuntimeError, OSError, ValueError) as exc:
        if project_dir and project_dir.exists():
            shutil.rmtree(project_dir, ignore_errors=True)

        raise ProjectUploadError(
            "Could not safely extract the uploaded ZIP file."
        ) from exc

    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)
