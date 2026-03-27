class Teacher:
    def __init__(self, id, name, expertise, assigned_classes, max_load):
        self.id = str(id) # Required for GA tracking
        self.teacher_name = name
        self.expertise = expertise
        self.assigned_classes = assigned_classes
        self.max_load_per_day = int(max_load)

class SchoolClass:
    def __init__(self, name, subjects, room):
        self.class_name = str(name).strip()
        # This attribute name must match what the scheduler calls
        self.assigned_subjects = [s.strip().lower() for s in str(subjects).split(',')]
        self.room_no = str(room).strip()