import random

class _FallbackTeacher:
    def __init__(self):
        self.id = "TBA_9999"
        self.teacher_name = "TBA"
        self.max_load_per_day = 999
        self.expertise = "all"
        self.assigned_classes = "all"

class Scheduling:
    def __init__(self, teachers, classes, subjects_config, timetable):
        self.teachers = teachers
        self.classes = classes
        self.subjects_config = subjects_config
        self.timetable = timetable
        self.weekly_tracker = {}
        self.teacher_schedule = {} 
        self.fallback_teacher = _FallbackTeacher()

    def _parse_list(self, item):
        """Safely converts item to a list of clean strings."""
        if isinstance(item, list):
            return [str(x).strip() for x in item]
        return [str(x).strip() for x in str(item).split(',')]

    def generate(self):
        """Builds a flawless timetable. Guarantees horizontal blocks, no vertical duplicates, and actively spaces out teachers."""
        if not self.classes or not self.timetable.days:
            return 

        days = list(self.timetable.days.keys())
        num_days = len(days)
        reference_day = self.timetable.get_day(days[0])
        active_slots = [i for i, s in enumerate(reference_day.slots) if not getattr(s, 'is_break', False)]
        num_slots = len(active_slots)

        # 1. Safely clear all assignments so frontend starts fresh
        for day_name in days:
            day_obj = self.timetable.get_day(day_name)
            for slot in day_obj.slots:
                slot.assigned_classes = []
                slot.assigned_teachers = []

        # MASTER TRACKERS to prevent Cross-Class Double Bookings
        teacher_busy = set() 
        daily_load = {}      

        for school_class in self.classes:
            assigned_subs = self._parse_list(school_class.assigned_subjects)
            if not assigned_subs:
                continue

            total_periods = num_slots * num_days
            needed_counts = {}

            for sub in assigned_subs:
                sub_clean = sub.upper()
                count = self.subjects_config.get(sub.lower(), {}).get('count', num_days)
                needed_counts[sub_clean] = min(count, num_days) 

            current_total = sum(needed_counts.values())
            if current_total < total_periods:
                diff = total_periods - current_total
                needed_counts["FREE"] = diff
            elif current_total > total_periods:
                diff = current_total - total_periods
                for _ in range(diff):
                    highest = max([s for s in needed_counts if s != "FREE"], key=needed_counts.get)
                    needed_counts[highest] -= 1

            # 2. THE UNBREAKABLE ROW BUILDER
            flat_subs = []
            sorted_subs = sorted(needed_counts.keys(), key=lambda x: needed_counts[x], reverse=True)
            for sub in sorted_subs:
                flat_subs.extend([sub] * needed_counts[sub])

            base_grid = [[None for _ in range(num_days)] for _ in range(num_slots)]
            for index, sub in enumerate(flat_subs):
                r = index // num_days
                c = index % num_days
                if r < num_slots:
                    base_grid[r][c] = sub

            # =====================================================================
            # 3. CROSS-CLASS COLLISION & CONSECUTIVE PENALTY SIMULATION
            # =====================================================================
            best_assignments = []
            min_penalty = float('inf')

            for attempt in range(50):
                test_grid = [row[:] for row in base_grid]
                random.shuffle(test_grid) 

                test_busy = set(teacher_busy)
                test_load = dict(daily_load)
                sim_penalty = 0  # 1000 pts for a TBA clash, 1 pt for a back-to-back class
                test_assignments = []

                for r, slot_idx in enumerate(active_slots):
                    current_sub = test_grid[r][0]
                    start_c = 0
                    count = 1
                    blocks = []
                    
                    for c in range(1, num_days):
                        if test_grid[r][c] == current_sub:
                            count += 1
                        else:
                            blocks.append((current_sub, start_c, count))
                            current_sub = test_grid[r][c]
                            start_c = c
                            count = 1
                    blocks.append((current_sub, start_c, count))

                    for sub, start_col, block_len in blocks:
                        block_days = days[start_col : start_col + block_len]
                        
                        if sub == "FREE":
                            teacher = self.fallback_teacher
                        else:
                            prev_slot_idx = slot_idx - 1
                            teacher, cons_score = self._find_perfect_teacher(sub, school_class, block_days, slot_idx, prev_slot_idx, test_busy, test_load)
                            
                            if not teacher:
                                teacher = self.fallback_teacher
                                sim_penalty += 1000 
                            else:
                                sim_penalty += cons_score 
                        
                        for day_name in block_days:
                            test_assignments.append((day_name, slot_idx, school_class, sub, teacher))
                            if teacher.id != "TBA_9999":
                                test_busy.add((str(teacher.id), day_name, slot_idx))
                                test_load[(str(teacher.id), day_name)] = test_load.get((str(teacher.id), day_name), 0) + 1

                if sim_penalty < min_penalty:
                    min_penalty = sim_penalty
                    best_assignments = test_assignments
                    if min_penalty == 0:
                        break 

            for day_name, slot_idx, sch_cls, sub, teacher in best_assignments:
                self._assign_direct(day_name, slot_idx, sch_cls, sub, teacher, teacher_busy, daily_load)

    def _find_perfect_teacher(self, sub, school_class, block_days, slot_idx, prev_slot_idx, test_busy, test_load):
        """Finds a teacher who is 100% free and actively scores them to avoid back-to-back periods."""
        sub_clean = sub.lower().strip()
        class_clean = school_class.class_name.strip().lower()
        
        qualified = []
        for t in self.teachers:
            t_exp = [e.lower() for e in self._parse_list(t.expertise)]
            t_classes = [c.lower() for c in self._parse_list(t.assigned_classes)]
            if sub_clean in t_exp and class_clean in t_classes:
                qualified.append(t)
                
        if not qualified:
            return None, 1000
            
        random.shuffle(qualified)
        perfect_teachers = []
        
        for t in qualified:
            t_id = str(t.id)
            max_load = int(float(t.max_load_per_day))
            
            is_perfect = True
            consecutive = 0
            
            for day_name in block_days:
                if (t_id, day_name, slot_idx) in test_busy or test_load.get((t_id, day_name), 0) >= max_load:
                    is_perfect = False
                    break
                
                if (t_id, day_name, prev_slot_idx) in test_busy:
                    consecutive += 1
                    
            if is_perfect:
                perfect_teachers.append({
                    'teacher': t,
                    'consecutive': consecutive
                })
                
        if perfect_teachers:
            perfect_teachers.sort(key=lambda x: x['consecutive'])
            best_choice = perfect_teachers[0]
            return best_choice['teacher'], best_choice['consecutive']
            
        return None, 1000 

    def _assign_direct(self, day_name, slot_idx, school_class, sub, teacher, teacher_busy, daily_load):
        """Safely writes the assignment directly to the backend UI arrays."""
        day_obj = self.timetable.get_day(day_name)
        
        # Shield to protect against Friday Half-Days (Early Closing)
        if slot_idx >= len(day_obj.slots):
            return
            
        assignment = {
            'subject': sub.upper(),
            'grade': school_class.class_name,
            'teacher': teacher,
            'room': school_class.room_no
        }
        
        if not hasattr(day_obj.slots[slot_idx], 'assigned_classes'):
            day_obj.slots[slot_idx].assigned_classes = []
        day_obj.slots[slot_idx].assigned_classes.append(assignment)
        
        if not hasattr(day_obj.slots[slot_idx], 'assigned_teachers'):
            day_obj.slots[slot_idx].assigned_teachers = []
        day_obj.slots[slot_idx].assigned_teachers.append(assignment)
        
        if teacher and teacher.id != "TBA_9999":
            t_id = str(teacher.id)
            if t_id not in self.teacher_schedule:
                self.teacher_schedule[t_id] = []
            self.teacher_schedule[t_id].append({
                'day': day_name, 'slot': slot_idx, **assignment
            })
            
            teacher_busy.add((t_id, day_name, slot_idx))
            daily_load[(t_id, day_name)] = daily_load.get((t_id, day_name), 0) + 1
            
        key = (school_class.class_name, sub.lower())
        self.weekly_tracker[key] = self.weekly_tracker.get(key, 0) + 1