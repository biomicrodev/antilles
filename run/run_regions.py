import logging.config

from antilles.pipeline.adjust import Adjuster
from antilles.pipeline.format import Formatter
from antilles.project import Project
from antilles.utils import profile

logging.config.fileConfig("../logging.ini")
log = logging.getLogger(__name__)


@profile(log=log)
def main():
    project_name = "OVARIAN-PDX"
    block_name = "DF106"

    step = 1
    project = Project(project_name)
    block = project.block(block_name)

    # === FINE ADJUST ================================================================ #
    if step == 0:
        adjuster = Adjuster(project, block)
        adjuster.run()

    # === PRE-FORMAT ================================================================= #
    elif step == 1:
        formatter = Formatter(project, block)
        formatter.run()


if __name__ == "__main__":
    main()
