import abc

import QuantLib as ql


class BondScheduleGenerator(abc.ABC):
    """
    Abstract Base Class for generating a bond schedule.
    Concrete implementations will override `generate` to produce a QuantLib Schedule.
    """

    @abc.abstractmethod
    def generate(self) -> ql.Schedule:
        pass
