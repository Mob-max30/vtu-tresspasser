import re


def parse_result_text(text: str) -> dict:
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    result = {
        "usn": None,
        "student_name": None,
        "cgpa": None,
        "pass_percentage": None,
        "semesters": [],
    }

    # -----------------------------
    # Basic student information
    # -----------------------------

    for i, line in enumerate(lines):
        if re.fullmatch(r"[A-Z0-9]{10}", line):
            result["usn"] = line

            if i > 0:
                result["student_name"] = lines[i - 1]

            break

    for i, line in enumerate(lines):
        if line == "CGPA" and i > 0:
            try:
                result["cgpa"] = float(lines[i - 1])
            except ValueError:
                pass

        if line == "PASS %" and i > 0:
            try:
                result["pass_percentage"] = float(lines[i - 1].replace("%", ""))
            except ValueError:
                pass

    # -----------------------------
    # Semester parsing
    # -----------------------------

    semester_pattern = re.compile(r"^Semester (\d+)$")

    current_semester = None

    for i, line in enumerate(lines):

        match = semester_pattern.match(line)

        if match:
            semester_number = int(match.group(1))

            # Find SGPA shortly after semester heading
            sgpa = None

            for next_line in lines[i + 1:i + 6]:
                if next_line.startswith("SGPA "):
                    try:
                        sgpa = float(next_line.split("SGPA ")[1])
                    except ValueError:
                        pass
                    break

            current_semester = {
                "semester": semester_number,
                "sgpa": sgpa,
                "subjects": [],
            }

            result["semesters"].append(current_semester)

            continue

        # -----------------------------
        # Subject rows
        # -----------------------------

        if current_semester is None:
            continue

        parts = line.split("\t")

        if len(parts) == 6:
            code, subject, ia, ea, total, status = parts

            # Ignore the table header
            if code == "SUB CODE":
                continue

            try:
                ia = int(ia)
                ea = int(ea)
                total = int(total)
            except ValueError:
                continue

            current_semester["subjects"].append(
                {
                    "code": code,
                    "name": subject,
                    "ia": ia,
                    "ea": ea,
                    "total": total,
                    "result": status,
                }
            )

    return result