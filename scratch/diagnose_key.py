"""Diagnostic: Verifies the full API key chain for Student C -> Course -> Instructor -> Groq."""
import sys
sys.path.insert(0, r"C:\Users\Lucas Aoki\.gemini\antigravity\scratch\course_platform")

from db.database import get_db
from db.models import User, Course, Enrollment
from repositories.user_repo import get_decrypted_groq_key
from groq import Groq

with get_db() as db:
    # 1. Find student C
    student = db.query(User).filter(User.username == "student C").first()
    print(f"[1] Student: {student.username} (ID {student.id})")

    # 2. Find their enrollment
    enrollment = db.query(Enrollment).filter(Enrollment.user_id == student.id).first()
    if not enrollment:
        print("[2] ERROR: Student C has no enrollments!")
        sys.exit()
    print(f"[2] Enrolled in Course ID: {enrollment.course_id}")

    # 3. Find the course and instructor
    course = db.query(Course).filter(Course.id == enrollment.course_id).first()
    print(f"[3] Course: '{course.title}', Instructor ID: {course.instructor_id}")

    # 4. Find the instructor and their key
    instructor = db.query(User).filter(User.id == course.instructor_id).first() if course.instructor_id else None
    if not instructor:
        print("[4] ERROR: Course has no instructor assigned!")
        sys.exit()

    has_key = bool(instructor.groq_key_encrypted)
    print(f"[4] Instructor: {instructor.username} (ID {instructor.id}), Has Key: {has_key}")

    if not has_key:
        print("[5] ERROR: Instructor has no API key in the database!")
        sys.exit()

    key = get_decrypted_groq_key(instructor)
    print(f"[5] Decrypted key: {key[:10] if key else 'None'}...")

    # 5. Test key against Groq
    print("[6] Testing key against Groq API...")
    try:
        client = Groq(api_key=key)
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10
        )
        print(f"[6] SUCCESS! Response: {resp.choices[0].message.content}")
    except Exception as e:
        print(f"[6] FAILED: {e}")
