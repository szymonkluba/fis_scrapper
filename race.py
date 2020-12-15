from datetime import datetime


class Race:
    participants = []
    disqualified = []
    is_cancelled = False

    def __init__(self, fis_id: int, place: str, subtitle: str, kind: str, date_starts: str, time_starts: str):
        self.fis_id = fis_id
        self.place = place
        self.subtitle = subtitle
        self.kind = kind
        self.date_starts = datetime.strptime(date_starts, '%B %d, %Y')
        self.time_starts = datetime.strptime(time_starts, "%H:%M")

    def set_status_to_cancelled(self):
        self.is_cancelled = True

    def add_participant(self, participant):
        self.participants.append(participant)

    def add_disqualified(self, disqualified):
        self.disqualified.append(disqualified)
