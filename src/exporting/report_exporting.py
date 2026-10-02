import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

import yaml
from loguru import logger

from src.customexceptions import PermanentError, TransientError
from src.reports.reports import Report


@dataclass
class ExportClosure:
    report: Report
    base_path: Path
    overwrite_existing: bool = False


class ReportExporter:
    def __init__(self):
        self.export_queue: list[ExportClosure] = []

    def extend_export_queue(self, reports: list[Report], base_path: Path) -> None:
        """
        > For each report, instantiate an ExportClosure.
        > Extend export queue with new closures.
        """
        new_pending = []
        for report in reports:
            new_pending.append(ExportClosure(report=report, base_path=base_path))

        self.export_queue.extend(new_pending)

    def export_reports(self, reports: list[Report], base_path: Path) -> None:
        """
        > Method exposed for Orchestrator.
        > Tries to export all items in the export queue
        > On TransientError, it does not pop from the queue,
          and leaves the closure for the next export batch.
        > On PermanentError, it raises.
        """
        self.extend_export_queue(reports, base_path)
        i = 0
        while i < len(self.export_queue):
            closure: ExportClosure = self.export_queue[i]
            try:
                self.export_report(closure)
                self.export_queue.pop(i)

            except TransientError:
                logger.info(
                    f"Could not export {closure.report.filename} due to a transient error."
                    "Exporting will be retried next time."
                )
                i += 1
                continue
            except PermanentError:
                logger.info(f"Could not export {closure.report.filename} due to a permanent error. Exiting...")
                raise

    def export_report(self, closure: ExportClosure) -> None:
        """Exports report to closure location."""

        report = closure.report
        export_base_path = closure.base_path

        path: Path = export_base_path / report.export_loc / report.filename
        temporary_path = None

        try:
            os.makedirs(path.parent, exist_ok=True)

            if closure.overwrite_existing:
                with tempfile.NamedTemporaryFile(
                    mode="w", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
                ) as f:
                    temporary_path = Path(f.name)
                    yaml.dump_all([report.to_dict()], f, sort_keys=False)
                os.replace(temporary_path, path)
            else:
                with open(path, "x") as f:
                    yaml.dump_all([report.to_dict()], f, sort_keys=False)

            logger.info(f"Successfully exported {report.filename} to {path}.")

        except FileExistsError as e:
            logger.error(f"{str(path)} already exists.")
            raise PermanentError(str(e))

        except OSError as e:
            logger.error(f"Could not export report to {str(path)}: {str(e)}.")
            raise TransientError(str(e))

        except yaml.YAMLError as e:
            logger.error(f"Could not serialize report to {str(path)}: {str(e)}")
            raise PermanentError(str(e))
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
