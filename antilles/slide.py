from typing import Union, Dict


class Slide:
    def __init__(
        self, project: str, block: str, panel: str, level: int, relpath: str = None
    ):
        self.project: str = project
        self.block: str = block
        self.panel: str = panel
        self.level: int = level

        self.relpath: str = relpath

    @property
    def project(self) -> str:
        return self.__project

    @project.setter
    def project(self, name: str):
        self.__project = name

    @property
    def block(self) -> str:
        return self.__block

    @block.setter
    def block(self, name: str):
        self.__block = name

    @property
    def panel(self) -> str:
        return self.__panel

    @panel.setter
    def panel(self, s: str):
        self.__panel = s

    @property
    def level(self) -> int:
        return self.__level

    @level.setter
    def level(self, l: Union[int, str]):
        self.__level = int(l)

    @property
    def relpath(self) -> str:
        return self.__relpath

    @relpath.setter
    def relpath(self, s: str):
        self.__relpath = s

    def to_dict(self) -> Dict[str, Union[str, int]]:
        return {
            "project": self.project,
            "block": self.block,
            "panel": self.panel,
            "level": self.level,
            "relpath": self.relpath,
        }
