from jump import Jump


class Participant:
    rank = 0
    bib = 0
    fis_code = 0
    name = ""
    year_born = 0
    nation = ""
    jumps = []
    total_points = 0.0
    diff_points = 0.0

    def __init__(self, rank: int):
        self.rank = rank

    def set_bib(self, bib: int):
        self.bib = bib

    def set_fis_code(self, fis_code: int):
        self.fis_code = fis_code

    def set_name(self, name: str):
        self.name = name

    def set_year_born(self, year_born: int):
        self.year_born = year_born

    def set_nation(self, nation: str):
        self.nation = nation

    def add_jump(self, jump: Jump):
        self.jumps.append(jump)

    def set_total_points(self, total_points: float):
        self.total_points = total_points

    def set_points_diff(self, points_diff: float):
        self.diff_points = points_diff
