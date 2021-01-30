from jump import Jump


class Participant:
    rank = 0
    bib = 0
    fis_code = 0
    name = ""
    year_born = 0
    nation = ""
    tot_points = 0.0
    diff_points = 0.0

    def __init__(self, rank: int):
        self.rank = rank
        self.jumps = []

    def add_jump(self, jump: Jump):
        self.jumps.append(jump)

    def __str__(self):
        line = (
            f"{self.rank if self.rank else ''};"
            f"{self.bib if self.bib else ''};"
            f"{self.fis_code if self.fis_code else ''};"
            f"{self.name if self.name else ''};"
            f"{self.year_born if self.year_born else ''};"
            f"{self.nation if self.nation else ''};"
        )
        for j in self.jumps:
            line += f"{j.distance if j.distance else ''};{j.points if j.points else ''};"
        line += f"{self.tot_points if self.tot_points else ''};"
        line += f"{self.diff_points if self.diff_points else ''}\n"
        return line
