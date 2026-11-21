import os
from langchain_core.tools import tool

COURSES = {
    1: [
        ("MS-251", "Probability & Statistics", 3.0),
        ("GE-160", "Applications of ICT", 3.0),
        ("GE-169", "Applied Physics", 3.0),
        ("GE-167", "Discrete Structures", 3.0),
        ("HQ-001", "Quran Translation - I", 0.5),
        ("GE-190", "Functional English", 3.0),
    ],
    2: [
        ("CC-112", "Programming Fundamentals", 3.0),
        ("CC-112-L", "Programming Fundamentals Lab", 1.0),
        ("CC-110", "Digital Logic Design", 2.0),
        ("CC-110-L", "Digital Logic Design Lab", 1.0),
        ("MS-252", "Linear Algebra", 3.0),
        ("GE-191", "Expository Writing", 3.0),
        ("GE-163", "Islamic Studies", 2.0),
        ("HQ-002", "Quran Translation - II", 0.5),
    ],
    3: [
        ("CC-211", "Object Oriented Programming", 3.0),
        ("CC-211-L", "Object Oriented Programming Lab", 1.0),
        ("CC-215", "Database Systems", 3.0),
        ("CC-215-L", "Database Systems Lab", 1.0),
        ("CC-210", "Computer Organization & Assembly Language", 3.0),
        ("GE-162", "Calculus & Analytical Geometry", 3.0),
        ("GE-192", "Introduction to Management", 2.0),
        ("HQ-003", "Quran Translation - III", 0.5),
    ],
    4: [
        ("CC-213", "Data Structures", 3.0),
        ("CC-213-L", "Data Structures Lab", 1.0),
        ("CC-312", "Information Security", 3.0),
        ("CC-214", "Computer Networks", 3.0),
        ("CC-212", "Software Engineering", 3.0),
        ("DC-220", "Advanced Database Management Systems", 3.0),
        ("HQ-004", "Quran Translation - IV", 0.5),
    ],
    5: [
        ("CC-313", "Analysis of Algorithms", 3.0),
        ("CC-310", "Artificial Intelligence", 3.0),
        ("DC-320", "Theory of Automata and Formal Languages", 3.0),
        ("DC-321", "Human Computer Interaction", 3.0),
        ("DC-322", "Computer Architecture", 3.0),
        ("EC-330", "Web Technologies / Elective", 3.0),
        ("HQ-005", "Quran Translation - V", 0.5),
    ],
    6: [
        ("CC-311", "Operating Systems", 3.0),
        ("EC-333", "Mobile Application Development / Elective", 3.0),
        ("EC-324", "Software Construction & Development / Elective", 3.0),
        ("EC-335", "Machine Learning / Elective", 3.0),
        ("EC-334", "Game Design and Development / Elective", 3.0),
        ("MS-253", "Multivariable Calculus", 3.0),
        ("HQ-006", "Quran Translation - VI", 0.5),
    ],
    7: [
        ("CC-411", "Final Year Project - I", 2.0),
        ("DC-328", "Parallel & Distributed Computing", 3.0),
        ("EC-345", "Computer Vision / Elective", 3.0),
        ("EC-425", "Software Quality Engineering / Elective", 3.0),
        ("MS-254", "Technical and Business Writing", 3.0),
        ("GE-263", "Entrepreneurship", 2.0),
        ("GE-262", "Professional Practices", 2.0),
        ("HQ-007", "Quran Translation - VII", 0.5),
    ],
    8: [
        ("CC-412", "Final Year Project - II", 4.0),
        ("DC-421", "Compiler Construction", 3.0),
        ("UE-272", "Introduction to Marketing", 3.0),
        ("GE-168", "Ideology and Constitution of Pakistan", 2.0),
        ("GE-363", "Civics and Community Engagement", 2.0),
        ("HQ-008", "Quran Translation - VIII", 0.5),
    ],
}

# Pre-computed semester credit hours
SEMESTER_CREDIT_HOURS = {s: sum(ch for _, _, ch in courses) for s, courses in COURSES.items()}


@tool
def marks_to_grade_points(marks: int) -> float:
    """Convert course marks (0-100) to PUCIT grade points using official grade bands.
    Use this tool whenever a student provides numerical marks for a course.
    """
    if marks < 0 or marks > 100:
        return "Error: marks must be between 0 and 100"

    if marks >= 85:
        return 4.0
    elif marks >= 80:
        return 3.7
    elif marks >= 75:
        return 3.3
    elif marks >= 70:
        return 3.0
    elif marks >= 65:
        return 2.7
    elif marks >= 61:
        return 2.3
    elif marks >= 58:
        return 2.0
    elif marks >= 55:
        return 1.7
    elif marks >= 50:
        return 1.0
    else:
        return 0.0


@tool
def calculate_semester_gpa(grade_points: list[float], credit_hours: list[float]) -> float:
    """Calculate one semester's credit-weighted GPA using formula: Σ(grade_point × credit_hours) / Σ(credit_hours).
    Use this tool when you have grade points and credit hours for all courses in a semester.
    """
    if not grade_points or not credit_hours:
        return "Error: grade_points and credit_hours cannot be empty"

    if len(grade_points) != len(credit_hours):
        return "Error: grade_points and credit_hours must have the same length"

    total_credits = sum(credit_hours)
    if total_credits <= 0:
        return "Error: total credit hours must be greater than zero"

    total_points = sum(gp * ch for gp, ch in zip(grade_points, credit_hours))
    return round(total_points / total_credits, 2)


@tool
def calculate_new_cgpa(
    current_cgpa: float,
    completed_credit_hours: float,
    semester_gpa: float,
    semester_credit_hours: float,
) -> float:
    """Project the new CGPA after completing a semester using:
    (current_cgpa * completed_ch + semester_gpa * semester_ch) / (completed_ch + semester_ch).
    Use this tool when a student asks where their CGPA will end up after a semester.
    """
    total_credits = completed_credit_hours + semester_credit_hours
    if total_credits <= 0:
        return "Error: total credit hours must be greater than zero"

    total_quality_points = (current_cgpa * completed_credit_hours) + (semester_gpa * semester_credit_hours)
    return round(total_quality_points / total_credits, 2)


@tool
def required_gpa_for_target(
    target_cgpa: float,
    current_cgpa: float,
    completed_credit_hours: float,
    remaining_credit_hours: float,
) -> float:
    """Calculate the GPA needed to reach a target CGPA over a credit hour horizon using:
    (target_cgpa * (completed_ch + remaining_ch) - current_cgpa * completed_ch) / remaining_ch.
    Use this tool for each progressive semester horizon when a student asks what GPA they need to reach their target.
    """
    if remaining_credit_hours <= 0:
        return "Error: remaining credit hours must be greater than zero"

    total_credits = completed_credit_hours + remaining_credit_hours
    needed_gpa = (target_cgpa * total_credits - current_cgpa * completed_credit_hours) / remaining_credit_hours
    return round(needed_gpa, 2)


@tool
def get_semester_courses(semester: int) -> str:
    """Return the official list of courses and credit hours for a given semester (1 to 8).
    Use this tool to find which courses belong to a semester and how many credit hours each has.
    For example, Semester 5 contains Analysis of Algorithms, Artificial Intelligence (AI), and Human Computer Interaction (HCI).
    """
    if semester < 1 or semester > 8:
        return "Error: semester must be between 1 and 8"

    courses = COURSES[semester]
    total_ch = SEMESTER_CREDIT_HOURS[semester]
    lines = [f"- {code}: {name} ({ch} credit hours)" for code, name, ch in courses]
    return f"Semester {semester} ({total_ch} total credit hours):\n" + "\n".join(lines)


@tool
def get_remaining_credit_hours(current_semester: int) -> float:
    """Total the graded credit hours remaining in the degree after a semester (sum of credit hours from current_semester + 1 to 8).
    Use this tool to find how many credit hours are left to graduate after a semester.
    """
    if current_semester < 1 or current_semester > 8:
        return "Error: semester must be between 1 and 8"

    remaining_semesters = range(current_semester + 1, 9)
    total_remaining = sum(SEMESTER_CREDIT_HOURS[s] for s in remaining_semesters)
    return float(total_remaining)


@tool
def save_report(filename: str, content: str) -> str:
    """Save a summary report to a text file and return a confirmation message.
    Use this tool ONLY when the student explicitly requests or agrees to save their calculation summary.
    """
    try:
        clean_name = os.path.basename(filename.strip())
        if not clean_name:
            clean_name = "report.txt"
        if not clean_name.endswith((".txt", ".md")):
            clean_name += ".txt"

        with open(clean_name, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Report successfully saved to {clean_name}"
    except Exception as e:
        return f"Error: failed to save report ({e})"
