#!/usr/bin/env python3
"""
Helper script to extract all step descriptions from step_generator.py
and generate Hebrew translations
"""

# All step descriptions with their Hebrew translations
STEP_TRANSLATIONS = {
    # Init steps
    "Init: Move rows motor to home position (X=0)": "אתחול: הזז מנוע שורות למיקום בית (X=0)",
    "Init: Move lines motor to home position (Y=0)": "אתחול: הזז מנוע קווים למיקום בית (Y=0)",
    "⚠️ Lifting line motor piston UP (preparing for upward movement to {position}cm)": "⚠️ הרמת בוכנת מנוע קווים למעלה (הכנה לתנועה עליונה ל-{position}ס״מ)",
    "Init: Move Y motor to {position}cm (paper + {height}cm ACTUAL high)": "אתחול: הזז מנוע Y ל-{position}ס״מ (נייר + {height}ס״מ גובה בפועל)",
    "Line motor piston DOWN (Y motor assembly lowered to default position)": "בוכנת מנוע קווים למטה (מכלול מנוע Y הונמך למצב ברירת מחדל)",

    # Cut edges
    "Cut top edge: Wait for LEFT X sensor": "חיתוך קצה עליון: המתן לחיישן X שמאלי",
    "Cut top edge: Open line cutter": "חיתוך קצה עליון: פתח חותך קווים",
    "Cut top edge: Wait for RIGHT X sensor": "חיתוך קצה עליון: המתן לחיישן X ימני",
    "Cut top edge: Close line cutter": "חיתוך קצה עליון: סגור חותך קווים",

    "Cut bottom edge: Wait for LEFT X sensor": "חיתוך קצה תחתון: המתן לחיישן X שמאלי",
    "Cut bottom edge: Open line cutter": "חיתוך קצה תחתון: פתח חותך קווים",
    "Cut bottom edge: Wait for RIGHT X sensor": "חיתוך קצה תחתון: המתן לחיישן X ימני",
    "Cut bottom edge: Close line cutter": "חיתוך קצה תחתון: סגור חותך קווים",

    "Cut RIGHT paper edge: Wait for TOP Y sensor": "חיתוך קצה ימני: המתן לחיישן Y עליון",
    "Cut RIGHT paper edge: Open row cutter": "חיתוך קצה ימני: פתח חותך שורות",
    "Cut RIGHT paper edge: Wait for BOTTOM Y sensor": "חיתוך קצה ימני: המתן לחיישן Y תחתון",
    "Cut RIGHT paper edge: Close row cutter": "חיתוך קצה ימני: סגור חותך שורות",

    "Cut LEFT paper edge: Wait for TOP Y sensor": "חיתוך קצה שמאלי: המתן לחיישן Y עליון",
    "Cut LEFT paper edge: Open row cutter": "חיתוך קצה שמאלי: פתח חותך שורות",
    "Cut LEFT paper edge: Wait for BOTTOM Y sensor": "חיתוך קצה שמאלי: המתן לחיישן Y תחתון",
    "Cut LEFT paper edge: Close row cutter": "חיתוך קצה שמאלי: סגור חותך שורות",

    # Dynamic descriptions with parameters
    "Move to first line of section {section}: {position}cm": "עבור לקו ראשון של חלק {section}: {position}ס״מ",
    "Move to line position: {position}cm": "עבור למיקום קו: {position}ס״מ",
    "Mark line {line}/{total} (Section {section}, Line {line_in_section})": "סמן קו {line}/{total} (חלק {section}, קו {line_in_section})",
    "Mark line {line}/{total} (Section {section}, Line {line_in_section}): Wait for LEFT X sensor": "סמן קו {line}/{total} (חלק {section}, קו {line_in_section}): המתן לחיישן X שמאלי",
    "Mark line {line}/{total} (Section {section}, Line {line_in_section}): Open line marker": "סמן קו {line}/{total} (חלק {section}, קו {line_in_section}): פתח סמן קווים",
    "Mark line {line}/{total} (Section {section}, Line {line_in_section}): Wait for RIGHT X sensor": "סמן קו {line}/{total} (חלק {section}, קו {line_in_section}): המתן לחיישן X ימני",
    "Mark line {line}/{total} (Section {section}, Line {line_in_section}): Close line marker": "סמן קו {line}/{total} (חלק {section}, קו {line_in_section}): סגור סמן קווים",

    # Section cuts
    "Move to cut between sections {section1} and {section2}: {position}cm": "עבור לחיתוך בין חלקים {section1} ו-{section2}: {position}ס״מ",
    "Cut between sections {section1} and {section2}: Wait for LEFT X sensor": "חיתוך בין חלקים {section1} ו-{section2}: המתן לחיישן X שמאלי",
    "Cut between sections {section1} and {section2}: Open line cutter": "חיתוך בין חלקים {section1} ו-{section2}: פתח חותך קווים",
    "Cut between sections {section1} and {section2}: Wait for RIGHT X sensor": "חיתוך בין חלקים {section1} ו-{section2}: המתן לחיישן X ימני",
    "Cut between sections {section1} and {section2}: Close line cutter": "חיתוך בין חלקים {section1} ו-{section2}: סגור חותך קווים",

    "Move to bottom cut position: {position}cm (paper starting position)": "עבור למיקום חיתוך תחתון: {position}ס״מ (מיקום התחלת נייר)",
    "Lines complete: Move lines motor to home position (Y=0)": "קווים הושלמו: הזז מנוע קווים למיקום בית (Y=0)",

    # Row marking
    "Rows operation: Ensure lines motor is at home position (Y=0)": "פעולת שורות: ודא שמנוע קווים במיקום בית (Y=0)",
    "Cut RIGHT paper edge: Move to {position}cm (ACTUAL width)": "חיתוך קצה ימני: עבור ל-{position}ס״מ (רוחב בפועל)",
    "Cut LEFT paper edge: Move to {position}cm (ACTUAL paper boundary)": "חיתוך קצה שמאלי: עבור ל-{position}ס״מ (גבול נייר בפועל)",

    # RTL Pages
    "RTL Page {page}/{total} (Section {section}, RTL Page {page_in_section}/{pages_per_section})": "עמוד RTL {page}/{total} (חלק {section}, עמוד RTL {page_in_section}/{pages_per_section})",
    "Move to RTL Page {page}/{total} (Section {section}, RTL Page {page_in_section}/{pages_per_section}) RIGHT edge: {position}cm": "עבור לעמוד RTL {page}/{total} (חלק {section}, עמוד RTL {page_in_section}/{pages_per_section}) קצה ימני: {position}ס״מ",
    "RTL Page {page}/{total} (Section {section}, RTL Page {page_in_section}/{pages_per_section}): Wait TOP Y sensor (RIGHT edge)": "עמוד RTL {page}/{total} (חלק {section}, עמוד RTL {page_in_section}/{pages_per_section}): המתן לחיישן Y עליון (קצה ימני)",
    "RTL Page {page}/{total} (Section {section}, RTL Page {page_in_section}/{pages_per_section}): Open row marker (RIGHT edge)": "עמוד RTL {page}/{total} (חלק {section}, עמוד RTL {page_in_section}/{pages_per_section}): פתח סמן שורות (קצה ימני)",
    "RTL Page {page}/{total} (Section {section}, RTL Page {page_in_section}/{pages_per_section}): Wait BOTTOM Y sensor (RIGHT edge)": "עמוד RTL {page}/{total} (חלק {section}, עמוד RTL {page_in_section}/{pages_per_section}): המתן לחיישן Y תחתון (קצה ימני)",
    "RTL Page {page}/{total} (Section {section}, RTL Page {page_in_section}/{pages_per_section}): Close row marker (RIGHT edge)": "עמוד RTL {page}/{total} (חלק {section}, עמוד RTL {page_in_section}/{pages_per_section}): סגור סמן שורות (קצה ימני)",

    "RTL: Move to RTL Page {page}/{total} (Section {section}, RTL Page {page_in_section}/{pages_per_section}) LEFT edge: {position}cm": "RTL: עבור לעמוד RTL {page}/{total} (חלק {section}, עמוד RTL {page_in_section}/{pages_per_section}) קצה שמאלי: {position}ס״מ",
    "RTL Page {page}/{total} (Section {section}, RTL Page {page_in_section}/{pages_per_section}): Wait TOP Y sensor (LEFT edge)": "עמוד RTL {page}/{total} (חלק {section}, עמוד RTL {page_in_section}/{pages_per_section}): המתן לחיישן Y עליון (קצה שמאלי)",
    "RTL Page {page}/{total} (Section {section}, RTL Page {page_in_section}/{pages_per_section}): Open row marker (LEFT edge)": "עמוד RTL {page}/{total} (חלק {section}, עמוד RTL {page_in_section}/{pages_per_section}): פתח סמן שורות (קצה שמאלי)",
    "RTL Page {page}/{total} (Section {section}, RTL Page {page_in_section}/{pages_per_section}): Wait BOTTOM Y sensor (LEFT edge)": "עמוד RTL {page}/{total} (חלק {section}, עמוד RTL {page_in_section}/{pages_per_section}): המתן לחיישן Y תחתון (קצה שמאלי)",
    "RTL Page {page}/{total} (Section {section}, RTL Page {page_in_section}/{pages_per_section}): Close row marker (LEFT edge)": "עמוד RTL {page}/{total} (חלק {section}, עמוד RTL {page_in_section}/{pages_per_section}): סגור סמן שורות (קצה שמאלי)",

    # Row section cuts
    "Move to cut between row sections {section1} and {section2}: {position}cm": "עבור לחיתוך בין חלקי שורות {section1} ו-{section2}: {position}ס״מ",
    "Cut between row sections {section1} and {section2}: Wait for TOP Y sensor": "חיתוך בין חלקי שורות {section1} ו-{section2}: המתן לחיישן Y עליון",
    "Cut between row sections {section1} and {section2}: Open row cutter": "חיתוך בין חלקי שורות {section1} ו-{section2}: פתח חותך שורות",
    "Cut between row sections {section1} and {section2}: Wait for BOTTOM Y sensor": "חיתוך בין חלקי שורות {section1} ו-{section2}: המתן לחיישן Y תחתון",
    "Cut between row sections {section1} and {section2}: Close row cutter": "חיתוך בין חלקי שורות {section1} ו-{section2}: סגור חותך שורות",

    "Rows complete: Move rows motor to home position (X=0)": "שורות הושלמו: הזז מנוע שורות למיקום בית (X=0)",

    # Program steps
    "=== Starting Program {program}: {name} (ACTUAL SIZE: {width}×{height}cm) ===": "=== מתחיל תוכנית {program}: {name} (גודל בפועל: {width}×{height}ס״מ) ===",
    "=== Program {program} completed: {width}×{height}cm paper processed ===": "=== תוכנית {program} הושלמה: נייר {width}×{height}ס״מ עובד ===",
}

if __name__ == "__main__":
    print("Total translations:", len(STEP_TRANSLATIONS))
    print("\nSample translations:")
    for eng, heb in list(STEP_TRANSLATIONS.items())[:5]:
        print(f"  {eng}")
        print(f"  -> {heb}\n")
