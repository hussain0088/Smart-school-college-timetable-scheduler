# timetable_logic.py
import datetime

class TimeSlot:
    def __init__(self, day, start_time, duration_minutes, slot_index):
        self.day = day.capitalize()
        self.start_time = start_time
        self.duration_minutes = int(duration_minutes)
        self.slot_index = slot_index
        self.is_break = False
        
        # Multi-class parallel scheduling
        self.assigned_classes = []


class DailySchedule:
    def __init__(self, day_name, start_time, duration, end_limit, break_after, break_duration):
        self.day_name = day_name.capitalize()
        self.slots = []
        self.current_time = start_time
        self.duration = int(duration)
        self.end_limit = end_limit
        self._generate_slots(break_after, break_duration)

    def _generate_slots(self, break_after, break_duration):
        count = 0
        while self._can_fit(self.duration):
            if count == break_after:
                self._add_break(break_duration)

            if self._can_fit(self.duration):
                self._add_period(count)
                count += 1
            else:
                break

    def _can_fit(self, minutes):
        h, m = map(int, self.current_time.split(':'))
        eh, em = map(int, self.end_limit.split(':'))
        return datetime.datetime(2000,1,1,h,m) + datetime.timedelta(minutes=minutes) <= datetime.datetime(2000,1,1,eh,em)

    def _add_period(self, idx):
        self.slots.append(TimeSlot(self.day_name, self.current_time, self.duration, idx))
        self._advance_time(self.duration)

    def _add_break(self, minutes):
        b = TimeSlot(self.day_name, self.current_time, minutes, -1)
        b.is_break = True
        self.slots.append(b)
        self._advance_time(minutes)

    def _advance_time(self, minutes):
        h, m = map(int, self.current_time.split(':'))
        self.current_time = (datetime.datetime(2000,1,1,h,m) + datetime.timedelta(minutes=minutes)).strftime("%H:%M")


class WeeklyTimetable:
    def __init__(self, school_name):
        self.school_name = school_name
        self.days = {}

    def create_week(self, days, start, dur, fri_limit, reg_limit, break_after, break_dur):
        for d in days:
            limit = fri_limit if d.lower()=="friday" else reg_limit
            self.days[d.capitalize()] = DailySchedule(d, start, dur, limit, break_after, break_dur)

    def get_day(self, day):
        return self.days.get(day.capitalize())
