School Timetable Generator
A smart, automated scheduling application designed to generate conflict-free school timetables.
This tool takes class requirements, teacher expertise, and subject loads into account to create a balanced weekly schedule.
Features
  Automated Scheduling: Generates weekly timetables based on CSV data inputs.
  Conflict Detection: Prevents teacher double-booking and room overlapping.
  Load Balancing: Respects max_load_per_day constraints for teaching staff.
  Interactive UI: Built with Streamlit for a user-friendly, web-based experience.
  Dynamic Data Management: Easily update teachers, subjects, and classes via CSV files.

Project Structure
  The system relies on three core data files to function
    File                                     Description
  Classes.csv               Contains class names (e.g., 9th-A), assigned subjects, and room numbers.
  teachers.csv              Lists teachers, their subject expertise, assigned sections, and daily period limits.
  subject data.csv          Defines subjects and the required number of periods per week.

Installation & Usage1 
	1. Prerequisites
	Ensure you have Python installed. You will also need the following libraries
		Bashpip install streamlit, pandas
	2. Running the App
		Bashstreamlit run app.py
	3. How to Use
		1. Prepare your Data: Update the .csv files in the root directory with your school's specific data.
		2.Generate: Use the sidebar or generate button in the app to process the constraints.
		3.Export: View the generated timetable for each class and export as needed.
Logic & Constraints
The algorithm follows these primary rules:
	1. Expertise Match: Teachers are only assigned to subjects listed in their expertise column.
	2. Room Assignment: Every class is tied to a specific room_no to prevent physical space conflicts.
	3. Workload: No teacher will be assigned more periods than their specified max_load_per_day.
