#!/usr/bin/env python3
"""
Hebrew Translation System for Scratch Desk CNC Control
======================================================

This module provides Hebrew translations for all user-facing UI elements.
Code, variable names, and technical terms remain in English.

Usage:
    from core.translations import t

    label_text = t("Connect Hardware")  # Returns: "התחבר לחומרה"
    formatted = t("X: {x:.2f} cm", x=5.5)  # Returns: "X: 5.50 ס״מ"
"""

import json
import os
import sys

# Platform-aware BiDi for Hebrew in Tkinter:
#   - Linux (Xft): NO native BiDi → must use python-bidi's get_display()
#   - macOS (Core Text): Native BiDi → get_display() would cause double-processing
#   - Windows (Uniscribe): Native BiDi → same as macOS
_NEEDS_BIDI_REORDER = (sys.platform == 'linux')
_bidi_get_display = None

if _NEEDS_BIDI_REORDER:
    try:
        from bidi.algorithm import get_display as _bidi_get_display
    except ImportError:
        print("WARNING: python-bidi not installed. Hebrew text will display incorrectly on Linux.")
        print("Install with: pip install python-bidi")
        _NEEDS_BIDI_REORDER = False

# Hebrew translations dictionary
# Organized by category for maintainability
HEBREW_TRANSLATIONS = {
    # ============================================================================
    # HARDWARE TEST GUI - Main Window
    # ============================================================================
    "Ultimate Hardware Test Interface - Scratch Desk": "ממשק בדיקת חומרה מתקדם - שולחן שריטה",
    "Motors & Position": "מנועים ומיקום",
    "Pistons & Sensors": "בוכנות וחיישנים",
    "GRBL Settings": "הגדרות GRBL",
    "GRBL": "GRBL",
    "Status & Logs": "סטטוס ולוגים",

    # ============================================================================
    # HARDWARE TEST GUI - Top Bar Status
    # ============================================================================
    "Hardware:": "חומרה:",
    "GRBL:": "GRBL:",
    "Not Connected": "לא מחובר",
    "Connected": "מחובר",
    "Port:": "פורט:",
    "Mode:": "מצב:",
    "Use Real Hardware": "השתמש בחומרה אמיתית",
    "Connect Hardware": "התחבר לחומרה",
    "Disconnect": "התנתק",
    "⚠ EMERGENCY STOP": "⚠ עצירת חירום",
    "Auto-detect": "זיהוי אוטומטי",

    # ============================================================================
    # HARDWARE TEST GUI - Motors Tab
    # ============================================================================
    "Current Position": "מיקום נוכחי",
    "X: {x:.2f} cm": "עמודות: {x:.2f} ס״מ",
    "Y: {y:.2f} cm": "שורות: {y:.2f} ס״מ",
    "Status:": "סטטוס:",
    "Idle": "מנוח",
    "Jog Control": "בקרת תנועה",
    "Step Size:": "גודל צעד:",
    "0.1mm": "0.1 מ״מ",
    "1mm": "1 מ״מ",
    "10mm": "10 מ״מ",
    "100mm": "100 מ״מ",
    "Y+↑": "↑שורות+",
    "←X-": "עמודות-←",
    "HOME": "בית",
    "X+→": "→עמודות+",
    "↓Y-": "שורות-↓",
    "Go to Position": "עבור למיקום",
    "X (cm):": "עמודות (ס״מ):",
    "Y (cm):": "שורות (ס״מ):",
    "Move": "הזז",
    "Preset Positions": "מיקומים מוגדרים מראש",
    "Origin (0, 0)": "נקודת התחלה (0, 0)",
    "Center (50, 35)": "מרכז (50, 35)",
    "Top Right (100, 0)": "ימין עליון (100, 0)",
    "Bottom Left (0, 70)": "שמאל תחתון (0, 70)",
    "Bottom Right (100, 70)": "ימין תחתון (100, 70)",
    "Movement Speed": "מהירות תנועה",
    "Slow": "איטי",
    "Normal": "רגיל",
    "Fast": "מהיר",
    "Limit Switches (Live)": "מתגי גבול (חי)",
    "Top Limit": "גבול עליון",
    "Bottom Limit": "גבול תחתון",
    "Left Limit": "גבול שמאלי",
    "Right Limit": "גבול ימני",
    "Door Sensor": "חיישן דלת",
    "OPEN": "פתוח",
    "CLOSED": "סגור",

    # ============================================================================
    # HARDWARE TEST GUI - Pistons Tab
    # ============================================================================
    "Piston Control": "בקרת בוכנות",
    "Line Marker": "סמן שורות",
    "Line Cutter": "חותך שורות",
    "Line Motor (Both)": "מנוע שורות (שניהם)",
    "Row Marker": "סמן עמודות",
    "Row Cutter": "חותך עמודות",
    "Air Pressure": "לחץ אוויר",
    "Air Pressure Valve": "שסתום לחץ אוויר",
    "↑ UP": "למעלה ↑",
    "↓ DOWN": "למטה ↓",
    "UNKNOWN": "לא ידוע",
    "Tool Position Sensors (Live)": "חיישני מיקום כלי (חי)",
    "UP Sensor": "חיישן עליון",
    "DOWN Sensor": "חיישן תחתון",
    "Left UP": "שמאל למעלה",
    "Left DOWN": "שמאל למטה",
    "Right UP": "ימין למעלה",
    "Right DOWN": "ימין למטה",
    "ACTIVE": "פעיל",
    "INACTIVE": "לא פעיל",
    "Edge Switches": "מתגי קצה",
    "X Left Edge": "קצה שמאלי שורות",
    "X Right Edge": "קצה ימני שורות",
    "Y Top Edge": "קצה עליון עמודות",
    "Y Bottom Edge": "קצה תחתון עמודות",

    # ============================================================================
    # HARDWARE TEST GUI - GRBL Tab
    # ============================================================================
    "Read Settings ($$)": "קרא הגדרות ($$)",
    "Apply Changes": "החל שינויים",
    "Apply (Session)": "החל (לפגישה)",
    "Save to Settings": "שמור להגדרות",
    "Save GRBL Settings": "שמור הגדרות GRBL",
    "Save GRBL configuration to settings.json and apply to hardware?": "לשמור הגדרות GRBL ל-settings.json ולהחיל על החומרה?",
    "Saving GRBL settings to settings.json...": "שומר הגדרות GRBL ל-settings.json...",
    "GRBL settings saved to settings.json": "הגדרות GRBL נשמרו ל-settings.json",
    "Applying settings to GRBL hardware...": "מחיל הגדרות על חומרת GRBL...",
    "Settings applied to GRBL hardware": "הגדרות הוחלו על חומרת GRBL",
    "System Config tab refreshed": "לשונית הגדרות מערכת רועננה",
    "Error saving GRBL settings: {error}": "שגיאה בשמירת הגדרות GRBL: {error}",
    "Settings applied (session only)": "הגדרות הוחלו (לפגישה בלבד)",
    "Max spindle speed": "מהירות ציר מקסימלית",
    "Min spindle speed": "מהירות ציר מינימלית",
    "Laser mode": "מצב לייזר",
    "Maximum spindle speed (RPM)": "מהירות ציר מקסימלית (RPM)",
    "Minimum spindle speed (RPM)": "מהירות ציר מינימלית (RPM)",
    "Laser mode enable (boolean)": "הפעלת מצב לייזר (בוליאני)",
    "Reset to Defaults": "איפוס לברירת מחדל",
    "Unlock ($X)": "בטל נעילה ($X)",
    "Home ($H)": "בית ($H)",
    "GRBL Configuration": "הגדרות GRBL",

    # GRBL Parameter descriptions
    "Step pulse time (microseconds)": "זמן דופק צעד (מיקרושניות)",
    "Step idle delay (milliseconds)": "השהיית מנוחת צעד (מילישניות)",
    "Step pulse invert mask": "מסכת היפוך דופק צעד",
    "Step direction invert mask": "מסכת היפוך כיוון צעד",
    "Invert step enable pin": "היפוך פין אפשור צעד",
    "Invert limit pins": "היפוך פיני גבול",
    "Invert probe pin": "היפוך פין בדיקה",
    "Status report options mask": "מסכת אפשרויות דוח סטטוס",
    "Junction deviation (mm)": "סטיית צומת (מ״מ)",
    "Arc tolerance (mm)": "סובלנות קשת (מ״מ)",
    "Report in inches": "דיווח באינצ'ים",
    "Soft limits enable": "אפשר גבולות רכים",
    "Hard limits enable": "אפשר גבולות קשיחים",
    "Homing cycle enable": "אפשר מחזור ביות",
    "Homing direction invert mask": "מסכת היפוך כיוון ביות",
    "Homing locate feed rate (mm/min)": "קצב הזנת איתור ביות (מ״מ/דקה)",
    "Homing search seek rate (mm/min)": "קצב חיפוש ביות (מ״מ/דקה)",
    "Homing switch debounce delay (ms)": "השהיית ניפוי רעש מתג ביות (מילישניות)",
    "Homing switch pull-off distance (mm)": "מרחק התנתקות מתג ביות (מ״מ)",
    "Maximum spindle speed (RPM)": "מהירות ציר מקסימלית (סל״ד)",
    "Minimum spindle speed (RPM)": "מהירות ציר מינימלית (סל״ד)",
    "Laser mode enable": "אפשר מצב לייזר",

    "Steps per mm for X axis": "צעדים למ״מ עבור ציר עמודות",
    "Steps per mm for Y axis": "צעדים למ״מ עבור ציר שורות",
    "Steps per mm for Z axis": "צעדים למ״מ עבור ציר Z",
    "Maximum rate for X axis (mm/min)": "קצב מקסימלי עבור ציר עמודות (מ״מ/דקה)",
    "Maximum rate for Y axis (mm/min)": "קצב מקסימלי עבור ציר שורות (מ״מ/דקה)",
    "Maximum rate for Z axis (mm/min)": "קצב מקסימלי עבור ציר Z (מ״מ/דקה)",
    "X axis acceleration (mm/sec²)": "תאוצת ציר עמודות (מ״מ/שנייה²)",
    "Y axis acceleration (mm/sec²)": "תאוצת ציר שורות (מ״מ/שנייה²)",
    "Z axis acceleration (mm/sec²)": "תאוצת ציר Z (מ״מ/שנייה²)",
    "X axis maximum travel (mm)": "מרחק נסיעה מקסימלי ציר עמודות (מ״מ)",
    "Y axis maximum travel (mm)": "מרחק נסיעה מקסימלי ציר שורות (מ״מ)",
    "Z axis maximum travel (mm)": "מרחק נסיעה מקסימלי ציר Z (מ״מ)",

    "G-code Commands & Console": "פקודות G-code וקונסולה",
    "Quick Commands": "פקודות מהירות",
    "Motion:": "תנועה:",
    "Modes:": "מצבים:",
    "Coords:": "קואורדינטות:",
    "Program:": "תוכנית:",
    "Query:": "שאילתה:",
    "G0 (Rapid)": "G0 (מהיר)",
    "G1 (Linear)": "G1 (ליניארי)",
    "G2 (Arc CW)": "G2 (קשת עם כיוון שעון)",
    "G3 (Arc CCW)": "G3 (קשת נגד כיוון שעון)",
    "G90 (Absolute)": "G90 (מוחלט)",
    "G91 (Relative)": "G91 (יחסי)",
    "G28 (Home)": "G28 (בית)",
    "Command:": "פקודה:",
    "Send": "שלח",
    "Response:": "תגובה:",

    # ============================================================================
    # HARDWARE TEST GUI - Console Tab
    # ============================================================================
    "Clear Log": "נקה לוג",
    "Save Log": "שמור לוג",
    "Auto-scroll": "גלילה אוטומטית",
    "Log Level:": "רמת לוג:",
    "DEBUG": "ניפוי באגים",
    "INFO": "מידע",
    "WARNING": "אזהרה",
    "ERROR": "שגיאה",
    "Ultimate Hardware Test GUI initialized": "ממשק בדיקת חומרה אותחל בהצלחה",
    "Click 'Connect Hardware' to begin testing": "לחץ על 'התחבר לחומרה' כדי להתחיל בדיקה",

    # ============================================================================
    # HARDWARE TEST GUI - Message Boxes
    # ============================================================================
    "Hardware Mode Changed": "מצב חומרה שונה",
    "Please disconnect and reconnect to apply the new hardware mode.": "אנא התנתק והתחבר מחדש כדי להחיל את מצב החומרה החדש.",
    "Connection Error": "שגיאת חיבור",
    "Failed to initialize hardware": "כשלון באתחול חומרה",
    "Failed to initialize hardware: {error}": "כשלון באתחול חומרה: {error}",
    "Please connect hardware first": "אנא התחבר לחומרה תחילה",
    "Error": "שגיאה",
    "Invalid position values": "ערכי מיקום לא תקינים",
    "Home Motors": "ביות מנועים",
    "Move all motors to home position (0, 0)?": "להזיז את כל המנועים למיקום בית (0, 0)?",
    "Emergency Stop": "עצירת חירום",
    "All motors stopped!\\nClick OK to resume.": "כל המנועים נעצרו!\\nלחץ אישור כדי להמשיך.",
    "Apply Settings": "החל הגדרות",
    "WARNING: Incorrect settings can damage hardware!\\n\\nAre you sure you want to apply these settings?": "אזהרה: הגדרות שגויות עלולות לפגוע בחומרה!\\n\\nהאם אתה בטוח שברצונך להחיל את ההגדרות הללו?",
    "Settings applied successfully": "ההגדרות הוחלו בהצלחה",
    "Failed to apply settings: {error}": "כשלון בהחלת הגדרות: {error}",
    "Reset Settings": "אפס הגדרות",
    "Reset GRBL to factory defaults?\\n\\nThis will reset ALL settings!": "לאפס את GRBL לברירת מחדל?\\n\\nזה יאפס את כל ההגדרות!",
    "Settings reset successfully": "ההגדרות אופסו בהצלחה",
    "Failed to reset settings: {error}": "כשלון באיפוס הגדרות: {error}",
    "Quit": "יציאה",
    "Disconnect hardware and quit?": "להתנתק מהחומרה ולצאת?",

    # ============================================================================
    # MAIN APPLICATION
    # ============================================================================
    "Scratch Desk Control System": "מערכת בקרת שולחן שריטה",
    "CSV Validation Errors": "שגיאות אימות CSV",
    "Found {n} validation errors": "נמצאו {n} שגיאות אימות",
    "No valid programs found in {path}": "לא נמצאו תוכניות תקינות ב-{path}",
    "System Ready - Load program to begin": "המערכת מוכנה - טען תוכנית כדי להתחיל",

    # ============================================================================
    # LEFT PANEL - Program Control
    # ============================================================================
    "PROGRAM CONTROL": "בקרת תוכנית",
    "Load CSV": "טען CSV",
    "No file loaded": "לא נטען קובץ",
    "File: {filename}": "קובץ: {filename}",
    "Program Selection:": "בחירת תוכנית:",
    "Program Parameters:": "פרמטרי תוכנית:",
    "Program Name:": "שם תוכנית:",
    "Program Number:": "מספר תוכנית:",
    "High (cm):": "גובה (ס״מ):",
    "Number of Lines:": "מספר שורות:",
    "Top Margin (cm):": "שוליים עליונים (ס״מ):",
    "Bottom Margin (cm):": "שוליים תחתונים (ס״מ):",
    "Width (cm):": "רוחב (ס״מ):",
    "Left Margin (cm):": "שוליים שמאליים (ס״מ):",
    "Right Margin (cm):": "שוליים ימניים (ס״מ):",
    "Page Width (cm):": "רוחב עמוד (ס״מ):",
    "Number of Pages:": "מספר עמודים:",
    "Buffer Between Pages (cm):": "מרווח בין עמודים (ס״מ):",
    "Repeat Rows:": "חזרה על עמודות:",
    "Repeat Lines:": "חזרה על שורות:",
    "Update Program": "עדכן תוכנית",
    "Validate": "אמת",
    "No program selected": "לא נבחרה תוכנית",
    "Program is valid": "התוכנית תקינה",

    # Paper Size Section
    "📐 ACTUAL PAPER SIZE (With Repeats)": "📐 גודל נייר בפועל (עם חזרות)",
    "Single Pattern:": "תבנית בודדת:",
    "{w:.1f} × {h:.1f} cm": "{w:.1f} × {h:.1f} ס״מ",
    "Repeats:": "חזרות:",
    "{rows} rows × {lines} lines": "{rows} עמודות × {lines} שורות",
    "🎯 ACTUAL SIZE NEEDED:": "🎯 גודל נדרש בפועל:",
    "{w:.1f} × {h:.1f} cm": "{w:.1f} × {h:.1f} ס״מ",
    "Line distance:": "מרחק בין קווים:",
    "{distance:.2f} cm": "{distance:.2f} ס״מ",
    "N/A (single line)": "(קו בודד) N/A",
    "✅ Fits on desk": "✅ מתאים לשולחן",
    "⚠️ Width exceeds desk": "⚠️ רוחב חורג מהשולחן",
    "⚠️ Height exceeds desk": "⚠️ גובה חורג מהשולחן",
    "⚠️ Exceeds desk size": "⚠️ חורג מגודל השולחן",

    # Validation Errors
    "Padding exceeds height: no room for lines": "השוליים חורגים מהגובה: אין מקום לקווים",
    "Line spacing too small ({spacing} cm, minimum {min} cm)": "מרחק בין קווים קטן מדי ({spacing} ס״מ, מינימום {min} ס״מ)",
    "Program has validation errors": "לתוכנית שגיאות אימות",
    "Number of lines must be greater than 0": "מספר שורות חייב להיות גדול מ-0",
    "Number of pages must be greater than 0": "מספר עמודים חייב להיות גדול מ-0",
    "Repeat rows must be greater than 0": "חזרה על עמודות חייבת להיות גדולה מ-0",
    "Repeat lines must be greater than 0": "חזרה על שורות חייבת להיות גדולה מ-0",
    "High must be greater than 0": "גובה חייב להיות גדול מ-0",
    "Width must be greater than 0": "רוחב חייב להיות גדול מ-0",
    "Page width must be greater than 0": "רוחב עמוד חייב להיות גדול מ-0",
    "Padding values cannot be negative": "ערכי שוליים לא יכולים להיות שליליים",
    "Margin values cannot be negative": "ערכי שוליים לא יכולים להיות שליליים",
    "Buffer between pages cannot be negative": "מרווח בין עמודים לא יכול להיות שלילי",

    # New Program Creation
    "Add New Program": "הוסף תוכנית חדשה",
    "NEW PROGRAM": "תוכנית חדשה",
    "Save Program": "שמור תוכנית",
    "Discard new program?": "למחוק את התוכנית החדשה?",
    "Program added successfully!": "התוכנית נוספה בהצלחה!",
    "Program name cannot be empty": "שם התוכנית לא יכול להיות ריק",
    "Program number {number} already exists": "מספר תוכנית {number} כבר קיים",
    "Cannot add program while execution is running": "לא ניתן להוסיף תוכנית בזמן ביצוע",
    "Delete Program": "מחיקת תוכנית",
    "Are you sure you want to delete program \"{name}\" (#{number})?": "האם אתה בטוח שברצונך למחוק את התוכנית \"{name}\" (#{number})?",
    "Cannot delete the last program": "לא ניתן למחוק את התוכנית האחרונה",
    "Cannot delete program while execution is running": "לא ניתן למחוק תוכנית בזמן ביצוע",

    # Message Boxes
    "Success": "הצלחה",
    "Program updated successfully!": "התוכנית עודכנה בהצלחה!",
    "Invalid value entered": "הוזן ערך לא תקין",
    "Failed to update program": "כשלון בעדכון התוכנית",
    "Failed to update program: {error}": "כשלון בעדכון התוכנית: {error}",

    # ============================================================================
    # RIGHT PANEL - Controls & Status
    # ============================================================================
    "CONTROLS & STATUS": "בקרות וסטטוס",
    "Generate Steps": "ייצר צעדים",
    "Step Navigation:": "ניווט צעדים:",
    "◄ Prev": "◄ הקודם",
    "Next ►": "הבא ►",
    "No steps loaded": "לא נטענו צעדים",
    "Steps Queue:": "תור צעדים:",
    "Current": "נוכחי",
    "All Steps": "כל הצעדים",
    "No step selected": "לא נבחר צעד",
    "Selected Step Details:": "פרטי צעד נבחר:",
    "Click on a step to view details...": "...לחץ על צעד כדי להציג פרטים",
    "Execution:": "ביצוע:",
    "▶ RUN": "▶ הפעל",
    "⏸ PAUSE": "⏸ השהה",
    "⏹ STOP": "⏹ עצור",
    "🔄 RESET": "🔄 אפס",
    "Ready": "מוכן",

    # Test Controls
    "🧪 TEST CONTROLS": "🧪 בקרות בדיקה",
    "📡 Sensors": "📡 חיישנים",
    "X:": "עמודות:",
    "Y:": "שורות:",
    "◄Left": "◄שמאל",
    "Right►": "ימין►",
    "▲Top": "▲עליון",
    "Bottom▼": "תחתון▼",
    "🔌 Limit Switches": "🔌 מתגי גבול",
    "Top": "עליון",
    "Bottom": "תחתון",
    "Right": "ימין",
    "Left": "שמאל",
    "Limit Switch": "מתג גבול",
    "🔧 Pistons (↓=checked)": "🔧 בוכנות (↓=מסומן)",
    "Lines:": "שורות:",
    "Rows:": "עמודות:",
    "Marker": "סמן",
    "Cutter": "חותך",
    "Motor": "מנוע",

    # Step Details Formatting
    "Operation: {op}\n": "פעולה: {op}\n",
    "Description: {desc}\n": "תיאור: {desc}\n",
    "Parameters: {params}": "פרמטרים: {params}",
    "Parameters:\n": "פרמטרים:\n",
    "Step {current}/{total}: {operation}": "צעד {current}/{total}: {operation}",
    "Step {current}/{total}\n\n": "צעד {current}/{total}\n\n",
    "Generated {steps} steps ({repeats} repetitions)": "נוצרו {steps} צעדים ({repeats} חזרות)",
    "Error generating steps: {error}": "שגיאה ביצירת צעדים: {error}",

    # Parameter Key Translations (for step details display)
    "program_number": "מספר תוכנית",
    "actual_width": "רוחב בפועל",
    "actual_height": "גובה בפועל",
    "repeat_rows": "חזרה על עמודות",
    "repeat_lines": "חזרה על שורות",
    "total_repeats": "סה״כ חזרות",
    "position": "מיקום",
    "tool": "כלי",
    "action": "פעולה",
    "sensor": "חיישן",
    "description": "תיאור",
    "line_marker": "סמן שורות",
    "line_cutter": "חותך שורות",
    "line_motor_piston": "בוכנת מנוע שורות",
    "row_marker": "סמן עמודות",
    "row_cutter": "חותך עמודות",
    "air_pressure": "לחץ אוויר",
    "air_pressure_valve": "שסתום לחץ אוויר",
    "down": "למטה",
    "up": "למעלה",

    # Status Messages
    "Generated {n} steps ({r} repetitions)": "נוצרו {n} צעדים ({r} חזרות)",
    "Error generating steps": "שגיאה ביצירת צעדים",
    "Error generating steps: {error}": "שגיאה ביצירת צעדים: {error}",
    "Complete system reset - All components restored to initial state": "איפוס מלא של המערכת - כל הרכיבים חזרו למצב התחלתי",
    "Test controls DISABLED - Real hardware mode active": "בקרות בדיקה מושבתות - מצב חומרה אמיתית פעיל",
    "Test controls ENABLED - Simulation mode active": "בקרות בדיקה מאופשרות - מצב סימולציה פעיל",

    # ============================================================================
    # CENTER PANEL - Canvas Visualization
    # ============================================================================
    "DESK SIMULATION": "סימולציית שולחן",
    "System Ready": "המערכת מוכנה",
    "Program ready - press Run to repeat": "התוכנית מוכנה - לחץ הפעל לחזרה",
    "⚠ EMERGENCY STOP - System stopped": "⚠ עצירת חירום - המערכת נעצרה",
    "📋 WORK OPERATIONS STATUS": "📋 סטטוס פעולות עבודה",
    "✏️ MARK": "✏️ סמן",
    "✂️ CUT": "✂️ חתוך",
    "Ready": "מוכן",
    "Working": "עובד",
    "Done": "הושלם",
    "Work": "עבודה",

    # ============================================================================
    # HARDWARE STATUS PANEL
    # ============================================================================
    "⚙️ HARDWARE STATUS": "⚙️ סטטוס חומרה",
    "🎯 MOTORS & SYSTEM": "🎯 מנועים ומערכת",
    "✏️ LINES": "✏️ שורות",
    "✂️ ROWS": "✂️ עמודות",
    "Tool Sensors": "חיישני כלי",
    "Edge Sensors": "חיישני קצה",
    "Pistons": "בוכנות",
    "X Position": "מיקום עמודות",
    "Y Position": "מיקום שורות",
    "Top Limit Switch": "מתג גבול עליון",
    "Bottom Limit Switch": "מתג גבול תחתון",
    "Right Limit Switch": "מתג גבול ימני",
    "Left Limit Switch": "מתג גבול שמאלי",
    "Marker ↑": "סמן ↑",
    "Marker ↓": "סמן ↓",
    "Cutter ↑": "חותך ↑",
    "Cutter ↓": "חותך ↓",
    "Motor L↑": "מנוע ש↑",
    "Motor L↓": "מנוע ש↓",
    "Motor R↑": "מנוע י↑",
    "Motor R↓": "מנוע י↓",
    "Marker Up Sensor": "חיישן סמן למעלה",
    "Marker Down Sensor": "חיישן סמן למטה",
    "Cutter Up Sensor": "חיישן חותך למעלה",
    "Cutter Down Sensor": "חיישן חותך למטה",
    "Motor Left Up": "מנוע שמאל למעלה",
    "Motor Left Down": "מנוע שמאל למטה",
    "Motor Right Up": "מנוע ימין למעלה",
    "Motor Right Down": "מנוע ימין למטה",
    "X Left Edge": "קצה שמאלי שורות",
    "X Right Edge": "קצה ימני שורות",
    "Y Top Edge": "קצה עליון עמודות",
    "Y Bottom Edge": "קצה תחתון עמודות",
    "Line Marker": "סמן שורות",
    "Line Cutter": "חותך שורות",
    "Motor Left": "מנוע שמאל",
    "Motor Right": "מנוע ימין",
    "Row Marker": "סמן עמודות",
    "Row Cutter": "חותך עמודות",
    "X Left": "שורות שמאל",
    "X Right": "שורות ימין",
    "Y Top": "עמודות עליון",
    "Y Bottom": "עמודות תחתון",
    "Mode:": "מצב:",
    "IDLE": "מנוח",
    "System ready": "המערכת מוכנה",
    "Progress:": "התקדמות:",
    "OFF": "כבוי",
    "ON": "פעיל",
    "TRIG": "מופעל",
    "READY": "מוכן",
    "UP": "למעלה",
    "DOWN": "למטה",

    # Operation Modes
    "BLOCKED": "חסום",
    "Waiting": "ממתין",
    "LINES": "שורות",
    "Marking lines": "מסמן שורות",
    "ROWS": "עמודות",
    "Cutting rows": "חותך עמודות",
    "System ready": "המערכת מוכנה",
    "SUCCESS": "הצלחה",
    "All done!": "!הכל הושלם",
    "FAIL": "כישלון",
    "Not completed": "לא הושלם",

    # ============================================================================
    # HARDWARE SETTINGS PANEL
    # ============================================================================
    "⚙️ Hardware Settings": "⚙️ הגדרות חומרה",
    "Hardware Mode:": "מצב חומרה:",
    "🖥️ Simulation": "🖥️ סימולציה",
    "🔧 Real Hardware": "🔧 חומרה אמיתית",
    "Arduino Port:": "פורט Arduino:",
    "🔄": "🔄",
    "● Simulation Mode Active": "● מצב סימולציה פעיל",
    "● Real Hardware Mode - Port: {port}": "● מצב חומרה אמיתית - פורט: {port}",
    "⚠️ Select a valid port to enable Real Hardware Mode": "⚠️ בחר פורט תקין כדי לאפשר מצב חומרה אמיתית",
    "✓ Apply Settings": "✓ החל הגדרות",
    "💾 Save to Config": "💾 שמור להגדרות",

    # MessageBoxes
    "Settings Applied": "הגדרות הוחלו",
    "Hardware settings updated": "הגדרות חומרה עודכנו",
    "⚠️ Please RESTART the application\\nto switch hardware modes.": "⚠️ אנא אתחל מחדש את האפליקציה\\nכדי לשנות מצב חומרה.",
    "Settings Saved": "הגדרות נשמרו",
    "Hardware settings saved to config": "הגדרות חומרה נשמרו להגדרות",
    "Save Error": "שגיאת שמירה",
    "Failed to save settings": "כשלון בשמירת הגדרות",
    "Failed to save settings: {error}": "כשלון בשמירת הגדרות: {error}",

    # ============================================================================
    # EXECUTION CONTROLLER
    # ============================================================================
    "Execution Running...": "...הביצוע רץ",
    "Execution Paused": "הביצוע הושהה",
    "Execution Stopped": "הביצוע נעצר",
    "Execution Completed": "הביצוע הושלם",
    "Program Completed Successfully!": "!התוכנית הושלמה בהצלחה",
    "Error: {message}": "שגיאה: {message}",
    "Executing step...": "...מבצע צעד",
    "Waiting for {sensor} sensor": "ממתין לחיישן {sensor}",

    # Sensor names (X sensors serve lines/שורות operations, Y sensors serve rows/עמודות operations)
    "x_left": "שורות שמאלי",
    "x_right": "שורות ימני",
    "y_top": "עמודות עליון",
    "y_bottom": "עמודות תחתון",
    "x": "שורות",
    "y": "עמודות",

    # Operation transitions and status messages
    "Lines": "שורות",
    "Rows": "עמודות",
    "✅ Safety resolved - {operation_type} execution resuming": "✅ בטיחות נפתרה - ביצוע {operation_type} ממשיך",
    "⏸️  Waiting: {from_op} → {to_op} transition": "⏸️  ממתין: מעבר מ-{from_op} ל-{to_op}",
    "{progress:.1f}% - Waiting for rows motor door CLOSED": "{progress:.1f}% - ממתין לדלת מנוע עמודות סגורה",
    "{progress:.1f}% - Rows motor door CLOSED, resuming...": "{progress:.1f}% - דלת מנוע עמודות סגורה, ממשיך...",
    "Transition to rows operations": "מעבר לפעולות עמודות",
    "▶️  Rows operations starting...": "▶️  פעולות עמודות מתחילות...",
    "SAFETY VIOLATION - Execution Stopped": "הפרת בטיחות - ביצוע נעצר",
    "Safety Violation": "הפרת בטיחות",
    "Safety Condition Detected": "תנאי בטיחות זוהה",
    "Emergency Stop": "עצירת חירום",
    "Safety Code:": "קוד בטיחות:",
    "Required Action:": "פעולה נדרשת:",
    "Detection Type:": "סוג זיהוי:",
    "Execution stopped due to safety violation!": "הביצוע נעצר עקב הפרת בטיחות!",
    "All motor movement has been halted to prevent damage.": "כל תנועת המנועים הופסקה כדי למנוע נזק.",
    "The system will remain stopped until you manually address this issue.": "המערכת תישאר עצורה עד שתטפל בבעיה באופן ידני.",
    "The system will AUTOMATICALLY RESUME when the condition is resolved.": "המערכת תמשיך אוטומטית כאשר התנאי ייפתר.",
    "Resolve the safety condition to continue.": "פתור את תנאי הבטיחות כדי להמשיך.",
    "Check the row marker position and resolve the safety condition.": "בדוק את מיקום סמן העמודות ופתור את תנאי הבטיחות.",
    "Unknown safety violation": "הפרת בטיחות לא ידועה",
    "Details": "פרטים",

    "{progress}% Complete ({step_index}/{total_steps} steps)": "{progress}% הושלם ({step_index}/{total_steps} צעדים)",
    "100% Complete - Execution finished": "100% הושלם - הביצוע הסתיים",
    "100% Complete - Success!": "!100% הושלם - הצלחה",
    "🚨 EMERGENCY STOP - Safety Violation": "🚨 עצירת חירום - הפרת בטיחות",
    "Execution has been immediately stopped due to a safety violation!": "!הביצוע נעצר מיידית עקב הפרת בטיחות",
    "Safety Code: {code}": "קוד בטיחות: {code}",
    "Detection: {type}": "זיהוי: {type}",
    "Details: {message}": "פרטים: {message}",
    "⚠️ All motor movement has been halted to prevent damage.": ".⚠️ כל תנועת המנועים הופסקה כדי למנוע נזק",
    "Please correct the safety issue before attempting to continue.": ".אנא תקן את בעיית הבטיחות לפני שמנסה להמשיך",

    # ============================================================================
    # BOTTOM PANEL - Status Bar
    # ============================================================================
    "STATUS:": "סטטוס:",

    # ============================================================================
    # COMMON TERMS & MESSAGES
    # ============================================================================
    "OK": "אישור",
    "Cancel": "ביטול",
    "Yes": "כן",
    "No": "לא",
    "Save": "שמור",
    "Load": "טען",
    "Close": "סגור",
    "Warning": "אזהרה",
    "Info": "מידע",
    "cm": "ס״מ",
    "mm": "מ״מ",
    "Step": "צעד",
    "steps": "צעדים",

    # ============================================================================
    # ADMIN TOOL - Main Window & Top Bar
    # ============================================================================
    "Admin Tool - Scratch Desk CNC": "כלי ניהול - שולחן שריטה CNC",
    "REAL HARDWARE": "חומרה אמיתית",
    "MOCK/SIMULATION": "הדמיה/סימולציה",
    "Mode: {mode}": "מצב: {mode}",
    "Not Available": "לא זמין",
    "GRBL Port:": "פורט GRBL:",
    "RS485 Port:": "פורט RS485:",
    "Change Admin Password": "שנה סיסמת מנהל",
    "EMERGENCY STOP": "עצירת חירום",
    "Mode: Unknown": "מצב: לא ידוע",

    # ============================================================================
    # ADMIN TOOL - Tab Names
    # ============================================================================
    "Safety Rules": "חוקי בטיחות",
    "System Config": "הגדרות מערכת",

    # ============================================================================
    # ADMIN TOOL - Motors Tab
    # ============================================================================
    "GRBL Status & Position": "סטטוס ומיקום GRBL",
    "State:": "מצב:",
    "Work Pos:": "מיקום עבודה:",
    "X: 0.00 Y: 0.00": "X: 0.00 Y: 0.00",
    "Start Homing Sequence": "התחל תהליך ביות",
    "Top Left (0, 0)": "שמאל עליון (0, 0)",
    "Test Position 1 (25, 25)": "מיקום בדיקה 1 (25, 25)",
    "Test Position 2 (75, 45)": "מיקום בדיקה 2 (75, 45)",

    # ============================================================================
    # ADMIN TOOL - GRBL Short Names
    # ============================================================================
    "Step pulse": "דופק צעד",
    "Step idle delay": "השהיית מנוחה",
    "Step port invert": "היפוך פורט צעד",
    "Direction port invert": "היפוך פורט כיוון",
    "Step enable invert": "היפוך אפשור צעד",
    "Limit pins invert": "היפוך פיני גבול",
    "Probe pin invert": "היפוך פין בדיקה",
    "Status report": "דוח סטטוס",
    "Junction deviation": "סטיית צומת",
    "Arc tolerance": "סובלנות קשת",
    "Report inches": "דיווח באינצ'ים",
    "Soft limits": "גבולות רכים",
    "Hard limits": "גבולות קשיחים",
    "Homing cycle": "מחזור ביות",
    "Homing dir invert": "היפוך כיוון ביות",
    "Homing feed": "הזנת ביות",
    "Homing seek": "חיפוש ביות",
    "Homing debounce": "ניפוי רעש ביות",
    "Homing pull-off": "התנתקות ביות",
    "X steps/mm": "צעדים/מ״מ X",
    "Y steps/mm": "צעדים/מ״מ Y",
    "Z steps/mm": "צעדים/מ״מ Z",
    "X Max rate": "קצב מקסימלי X",
    "Y Max rate": "קצב מקסימלי Y",
    "Z Max rate": "קצב מקסימלי Z",
    "X Acceleration": "תאוצה X",
    "Y Acceleration": "תאוצה Y",
    "Z Acceleration": "תאוצה Z",
    "X Max travel": "נסיעה מקסימלית X",
    "Y Max travel": "נסיעה מקסימלית Y",
    "Z Max travel": "נסיעה מקסימלית Z",

    # GRBL Tooltip Descriptions (admin tool specific)
    "Step port invert mask": "מסכת היפוך פורט צעד",
    "Direction port invert mask": "מסכת היפוך פורט כיוון",
    "Step enable invert (boolean)": "היפוך אפשור צעד (בוליאני)",
    "Limit pins invert (boolean)": "היפוך פיני גבול (בוליאני)",
    "Probe pin invert (boolean)": "היפוך פין בדיקה (בוליאני)",
    "Status report mask": "מסכת דוח סטטוס",
    "Report in inches (boolean)": "דיווח באינצ'ים (בוליאני)",
    "Soft limits enable (boolean)": "אפשור גבולות רכים (בוליאני)",
    "Hard limits enable (boolean)": "אפשור גבולות קשיחים (בוליאני)",
    "Homing cycle enable (boolean)": "אפשור מחזור ביות (בוליאני)",
    "Homing feed rate (mm/min)": "קצב הזנת ביות (מ״מ/דקה)",
    "Homing seek rate (mm/min)": "קצב חיפוש ביות (מ״מ/דקה)",
    "Homing debounce (milliseconds)": "ניפוי רעש ביות (מילישניות)",
    "Homing pull-off distance (mm)": "מרחק התנתקות ביות (מ״מ)",
    "Maximum travel for X axis (mm)": "נסיעה מקסימלית ציר X (מ״מ)",
    "Maximum travel for Y axis (mm)": "נסיעה מקסימלית ציר Y (מ״מ)",
    "Maximum travel for Z axis (mm)": "נסיעה מקסימלית ציר Z (מ״מ)",

    # ============================================================================
    # ADMIN TOOL - Connection Messages
    # ============================================================================
    "Admin Tool initialized": "כלי הניהול אותחל",
    "Click 'Connect Hardware' to begin": "לחץ 'התחבר לחומרה' כדי להתחיל",
    "Admin Tool opened from main app (shared hardware connection)": "כלי הניהול נפתח מהאפליקציה הראשית (חיבור חומרה משותף)",
    "Hardware mode changed to: {mode}": "מצב חומרה שונה ל: {mode}",
    "Please disconnect and reconnect to apply hardware mode change": "אנא התנתק והתחבר מחדש כדי להחיל את שינוי מצב החומרה",
    "Failed to update hardware mode: {error}": "כשלון בעדכון מצב חומרה: {error}",
    "Found {count} serial port(s)": "נמצאו {count} פורטים סריאליים",
    "Error scanning ports: {error}": "שגיאה בסריקת פורטים: {error}",
    "Auto-initializing hardware...": "מאתחל חומרה אוטומטית...",
    "Connecting to hardware...": "מתחבר לחומרה...",
    "Using selected GRBL port: {port}": "משתמש בפורט GRBL שנבחר: {port}",
    "Using selected RS485 port: {port}": "משתמש בפורט RS485 שנבחר: {port}",
    "Hardware mode: {mode}": "מצב חומרה: {mode}",
    "Hardware connected successfully": "החומרה חוברה בהצלחה",
    "GRBL connected successfully": "GRBL חובר בהצלחה",
    "Disconnecting from hardware...": "מתנתק מהחומרה...",
    "Hardware disconnected": "החומרה נותקה",
    "Monitor loop started": "לולאת ניטור התחילה",
    "Monitor error: {error}": "שגיאת ניטור: {error}",

    # ============================================================================
    # ADMIN TOOL - Motor Control Messages
    # ============================================================================
    "Not Connected": "לא מחובר",
    "Please connect hardware first": "אנא התחבר לחומרה תחילה",
    "Jogging X to {pos:.2f}cm": "מזיז עמודות ל-{pos:.2f} ס״מ",
    "Jogging Y to {pos:.2f}cm": "מזיז שורות ל-{pos:.2f} ס״מ",
    "Jog error: {error}": "שגיאת תנועה: {error}",
    "Moving to X={x:.2f}, Y={y:.2f}": "נע ל-X={x:.2f}, Y={y:.2f}",
    "Move complete": "התנועה הושלמה",
    "Moving to preset X={x:.2f}, Y={y:.2f}": "נע למיקום מוגדר X={x:.2f}, Y={y:.2f}",
    "Move all motors to home (0, 0)?": "להזיז את כל המנועים לבית (0, 0)?",
    "Homing all motors...": "מבצע ביות לכל המנועים...",
    "Motors homed": "המנועים בוצתו",
    "EMERGENCY STOP!": "עצירת חירום!",
    "All motors stopped!": "כל המנועים נעצרו!",
    "Emergency stop cleared": "עצירת חירום בוטלה",
    "GRBL Not Connected": "GRBL לא מחובר",
    "GRBL is not connected.": "GRBL לא מחובר.",
    "Start Homing": "התחל ביות",
    "Start complete homing sequence?": "להתחיל תהליך ביות מלא?",
    "Starting homing sequence...": "מתחיל תהליך ביות...",
    "Homing complete": "הביות הושלם",
    "Homing failed: {error}": "הביות נכשל: {error}",
    "Homing error: {error}": "שגיאת ביות: {error}",

    # ============================================================================
    # HOMING DIALOG
    # ============================================================================
    "Homing in Progress": "ביות בתהליך",
    "Homing in Progress...": "ביות בתהליך...",
    "1. Apply GRBL configuration": "1. החלת הגדרות GRBL",
    "2. Check door is open": "2. בדיקה שהדלת פתוחה",
    "3. Lift line motor pistons": "3. הרמת בוכנות מנוע שורות",
    "4. Run GRBL homing ($H)": "4. הפעלת ביות GRBL ($H)",
    "5. Reset work coordinates to (0,0)": "5. איפוס קואורדינטות עבודה ל-(0,0)",
    "6. Lower line motor pistons": "6. הורדת בוכנות מנוע שורות",
    "Homing Failed": "הביות נכשל",
    "Homing sequence failed!\n\nError: {error}": "תהליך הביות נכשל!\n\nשגיאה: {error}",
    "Homing Complete": "הביות הושלם",
    "Homing sequence completed successfully!\n\nMachine is now at home position (0, 0).": "תהליך הביות הושלם בהצלחה!\n\nהמכונה נמצאת כעת במיקום בית (0, 0).",
    "Door is closed - please open the door to continue": "הדלת סגורה - נא לפתוח את הדלת כדי להמשיך",

    # Admin Tool button and login
    "Admin Tool": "כלי ניהול",
    "Admin Login": "כניסת מנהל",
    "Enter admin password:": "הזן סיסמת מנהל:",
    "Wrong password": "סיסמה שגויה",
    "Login": "כניסה",

    # Startup homing confirmation
    "Homing Required": "נדרש ביות",
    "Real hardware mode is active.\n\nThe machine needs to be homed before operation.\nThis will:\n1. Apply GRBL configuration\n2. Check door is open\n3. Lift line motor pistons\n4. Run GRBL homing ($H)\n5. Reset work coordinates\n6. Lower line motor pistons\n\nMake sure the machine is clear and ready.\n\nRun homing now?": "מצב חומרה אמיתית פעיל.\n\nיש לבצע ביות למכונה לפני הפעלה.\nפעולה זו תבצע:\n1. החלת הגדרות GRBL\n2. בדיקה שהדלת פתוחה\n3. הרמת בוכנות מנוע שורות\n4. הפעלת ביות GRBL ($H)\n5. איפוס קואורדינטות עבודה\n6. הורדת בוכנות מנוע שורות\n\nוודא שהמכונה פנויה ומוכנה.\n\nלהפעיל ביות עכשיו?",
    "Machine was NOT homed.\n\nYou can run homing later from the Hardware Test GUI\nor by switching hardware modes in the settings panel.": "המכונה לא עברה ביות.\n\nניתן להפעיל ביות מאוחר יותר מממשק בדיקת החומרה\nאו על ידי החלפת מצב חומרה בלוח ההגדרות.",

    # Manual homing confirmation
    "Run Homing": "הפעל ביות",
    "Cannot Home": "לא ניתן לבצע ביות",
    "Cannot run homing while a program is executing.\nStop execution first.": "לא ניתן לבצע ביות בזמן שתוכנית רצה.\nעצור את הביצוע קודם.",
    "This will run the homing sequence.\n\nMake sure the machine is clear and ready.\n\nRun homing now?": "פעולה זו תפעיל את תהליך הביות.\n\nוודא שהמכונה פנויה ומוכנה.\n\nלהפעיל ביות עכשיו?",

    # Homing status
    "HOMING": "ביות",
    "Running homing sequence...": "מבצע תהליך ביות...",

    # ============================================================================
    # ADMIN TOOL - Piston Control Messages
    # ============================================================================
    "Raising {name}": "מרים {name}",
    "{name} raised": "{name} הורם",
    "Lowering {name}": "מוריד {name}",
    "{name} lowered": "{name} הורד",

    # ============================================================================
    # ADMIN TOOL - GRBL Settings Messages
    # ============================================================================
    "Reading GRBL settings...": "קורא הגדרות GRBL...",
    "GRBL settings loaded": "הגדרות GRBL נטענו",
    "Error reading settings: {error}": "שגיאה בקריאת הגדרות: {error}",
    "Apply changes to GRBL?": "להחיל שינויים ל-GRBL?",
    "Applying GRBL settings...": "מחיל הגדרות GRBL...",
    "Settings applied": "ההגדרות הוחלו",
    "Error applying settings: {error}": "שגיאה בהחלת הגדרות: {error}",
    "Reset GRBL to factory defaults?": "לאפס GRBL לברירת מחדל יצרן?",
    "GRBL reset to defaults": "GRBL אופס לברירת מחדל",
    "Error resetting: {error}": "שגיאה באיפוס: {error}",
    "GRBL unlocked": "GRBL שוחרר",
    "Error unlocking: {error}": "שגיאה בשחרור נעילה: {error}",
    "GRBL homing completed": "ביות GRBL הושלם",
    "Sending: {command}": "שולח: {command}",
    "Response: {response}": "תגובה: {response}",
    "Error sending: {error}": "שגיאה בשליחה: {error}",

    # ============================================================================
    # ADMIN TOOL - Console & Log Messages
    # ============================================================================
    "Log cleared": "הלוג נוקה",
    "Log saved to {filename}": "הלוג נשמר ב-{filename}",
    "Failed to save: {error}": "כשלון בשמירה: {error}",

    # ============================================================================
    # ADMIN TOOL - Password Dialog
    # ============================================================================
    "New Password:": "סיסמה חדשה:",
    "Confirm Password:": "אשר סיסמה:",
    "Password cannot be empty": "הסיסמה לא יכולה להיות ריקה",
    "Passwords do not match": "הסיסמאות לא תואמות",
    "Admin password changed": "סיסמת מנהל שונתה",
    "Admin password changed successfully.": "סיסמת מנהל שונתה בהצלחה.",
    "Failed to change password: {error}": "כשלון בשינוי סיסמה: {error}",
    "Disconnect and quit?": "להתנתק ולצאת?",

    # ============================================================================
    # ADMIN TOOL - Config Tab
    # ============================================================================
    "Search:": "חיפוש:",
    "Clear": "נקה",
    "Save Changes": "שמור שינויים",
    "Revert": "בטל שינויים",
    "Backup": "גיבוי",
    "Restore": "שחזור",
    "Refresh": "רענן",
    "Categories": "קטגוריות",
    "Settings Editor": "עורך הגדרות",
    "Setting: {path}": "הגדרה: {path}",
    "Enabled": "מופעל",
    "Disabled": "מושבת",
    "Edit List: {key}": "ערוך רשימה: {key}",
    "Edit list items (one per line):": "ערוך פריטי רשימה (אחד בכל שורה):",
    "Edit List...": "ערוך רשימה...",
    "Default: {default}": "ברירת מחדל: {default}",
    "No Changes": "אין שינויים",
    "There are no pending changes to save.": "אין שינויים ממתינים לשמירה.",
    "Save {num_changes} pending change(s)?": "לשמור {num_changes} שינויים ממתינים?",
    "Settings saved successfully.": "ההגדרות נשמרו בהצלחה.",
    "Saved {num_changes} configuration changes": "{num_changes} שינויי הגדרות נשמרו",
    "There are no pending changes to revert.": "אין שינויים ממתינים לביטול.",
    "Revert Changes": "בטל שינויים",
    "Revert {num_changes} pending change(s)?": "לבטל {num_changes} שינויים ממתינים?",
    "Changes reverted.": "השינויים בוטלו.",
    "Backup Created": "גיבוי נוצר",
    "Backup saved to:\n{backup_file}": "גיבוי נשמר ב:\n{backup_file}",
    "Failed to create backup": "כשלון ביצירת גיבוי",
    "No Backups": "אין גיבויים",
    "No backup files found.": "לא נמצאו קבצי גיבוי.",
    "Restore Backup": "שחזר גיבוי",
    "Select backup to restore:": "בחר גיבוי לשחזור:",
    "No Selection": "לא נבחר",
    "Please select a backup file.": "אנא בחר קובץ גיבוי.",
    "Settings restored successfully.": "ההגדרות שוחזרו בהצלחה.",
    "Unsaved Changes": "שינויים לא שמורים",
    "You have unsaved changes. Refresh anyway?": "יש לך שינויים לא שמורים. לרענן בכל זאת?",
    "{num_changes} unsaved change(s)": "{num_changes} שינויים לא שמורים",
    "No unsaved changes": "אין שינויים לא שמורים",
    "Settings file: {file}": "קובץ הגדרות: {file}",
    "Failed to save settings: {error}": "כשלון בשמירת הגדרות: {error}",

    # ============================================================================
    # ADMIN TOOL - Safety Tab
    # ============================================================================
    "Global Safety:": "בטיחות גלובלית:",
    "+ Add Rule": "הוסף חוק +",
    "Import": "ייבוא",
    "Export": "ייצוא",
    "On": "פעיל",
    "Rule Name": "שם חוק",
    "Severity": "חומרה",
    "Type": "סוג",
    "Edit": "עריכה",
    "Delete": "מחיקה",
    "Enable/Disable": "הפעל/השבת",
    "Rule Details": "פרטי חוק",
    "ID:": "מזהה:",
    "Name:": "שם:",
    "Priority:": "עדיפות:",
    "Severity:": "חומרה:",
    "Description:": "תיאור:",
    "Conditions:": "תנאים:",
    "Blocks:": "חוסם:",
    "Recent Violations": "הפרות אחרונות",
    "System": "מערכת",
    "Custom": "מותאם אישית",
    "Disable Safety": "השבת בטיחות",
    "WARNING: Disabling the safety system can lead to hardware damage!\n\nAre you sure you want to disable safety checks?": "אזהרה: השבתת מערכת הבטיחות עלולה לגרום נזק לחומרה!\n\nהאם אתה בטוח שברצונך להשבית את בדיקות הבטיחות?",
    "Global safety system {status}": "מערכת בטיחות גלובלית {status}",
    "ENABLED": "מופעלת",
    "DISABLED": "מושבתת",
    "Cannot Delete": "לא ניתן למחוק",
    "System rules cannot be deleted. You can only disable them.": "חוקי מערכת לא ניתנים למחיקה. ניתן רק להשבית אותם.",
    "Delete Rule": "מחק חוק",
    "Delete rule '{name}'?": "למחוק את החוק '{name}'?",
    "Import Safety Rules": "ייבוא חוקי בטיחות",
    "Import Rules": "ייבוא חוקים",
    "Merge with existing rules? (No = Replace all)": "למזג עם חוקים קיימים? (לא = החלף הכל)",
    "Rules imported successfully": "החוקים יובאו בהצלחה",
    "Invalid rules file format": "פורמט קובץ חוקים לא תקין",
    "Failed to import rules: {error}": "כשלון בייבוא חוקים: {error}",
    "Export Safety Rules": "ייצוא חוקי בטיחות",
    "Rules exported to {filename}": "החוקים יוצאו ל-{filename}",
    "Failed to export rules: {error}": "כשלון בייצוא חוקים: {error}",
    "System Active": "המערכת פעילה",
    "System DISABLED": "המערכת מושבתת",
    "Failed to save rules: {error}": "כשלון בשמירת חוקים: {error}",

    # Safety Tab - Rule Editor
    "Add New Rule": "הוסף חוק חדש",
    "Edit Rule": "ערוך חוק",
    "Rule ID:": "מזהה חוק:",
    "Conditions (when these are TRUE, operation is BLOCKED)": "תנאים (כשאלה נכונים, הפעולה נחסמת)",
    "Match:": "התאמה:",
    "ALL conditions (AND)": "כל התנאים (וגם)",
    "ANY condition (OR)": "אחד מהתנאים (או)",
    "+ Add Condition": "הוסף תנאי +",
    "Blocked Operations": "פעולות חסומות",
    "+ Add Blocked Operation": "הוסף פעולה חסומה +",
    "Error Message:": "הודעת שגיאה:",
    "Rule ID is required": "מזהה חוק נדרש",
    "Rule name is required": "שם חוק נדרש",
    "(lower = higher priority)": "(נמוך = עדיפות גבוהה)",
    "Tools:": "כלים:",
    "Dir:": "כיוון:",
    "Exclude setup movements": "אל תכלול תנועות הכנה",

    # Safety Tab - Operation Descriptions
    "Move X-axis (rows motor) - horizontal movement": "הזז ציר X (מנוע עמודות) - תנועה אופקית",
    "Move Y-axis (lines motor) - vertical movement": "הזז ציר Y (מנוע שורות) - תנועה אנכית",
    "Tool operations (pistons up/down)": "פעולות כלי (בוכנות למעלה/למטה)",
    "Wait for sensor trigger": "המתן להפעלת חיישן",

    # Safety Tab - Condition Display
    "No conditions": "אין תנאים",
    "None": "אין",
    "(except setup)": "(למעט הכנה)",

    # Safety Tab - Condition Type Labels
    "Pistons": "בוכנות",
    "Sensor": "חיישן",
    "Position": "מיקום",

    # Safety Tab - Condition type lowercase (for dropdown mapping)
    "piston": "בוכנות",

    # Safety Tab - Operator display names
    "equals": "שווה",
    "not_equals": "לא שווה",
    "greater_than": "גדול מ",
    "less_than": "קטן מ",

    # Safety Tab - Severity display
    "critical": "קריטי",

    # Safety Tab - Reason types
    "Operational": "תפעולי",
    "Collision": "התנגשות",
    "Mechanical": "מכני",

    # Safety Tab - Real-Time Monitoring section
    "Real-Time Monitoring": "ניטור בזמן אמת",
    "Enable real-time monitoring": "הפעל ניטור בזמן אמת",
    "Operation context:": "הקשר פעולה:",
    "Action:": "פעולה:",
    "Recovery action:": "פעולת התאוששות:",
    "Recovery Conditions (when these are TRUE, auto-resume):": "תנאי התאוששות (כשאלה נכונים, חידוש אוטומטי):",
    "ALL (AND)": "כל התנאים (וגם)",
    "ANY (OR)": "אחד מהתנאים (או)",
    "+ Add Recovery Condition": "הוסף תנאי התאוששות +",
    "Pre-step only": "לפני צעד בלבד",
    "Reason:": "סיבה:",
    "Real-time:": "זמן אמת:",

    # Safety Tab - Monitor action/recovery display
    "emergency_pause": "השהייה חירום",
    "auto_resume": "חידוש אוטומטי",

    # Safety Tab - Operation short display names (for dropdowns)
    "move_x": "תנועת ציר X",
    "move_y": "תנועת ציר Y",
    "move_position": "תנועה למיקום",
    "tool_action": "פעולת כלי",
    "wait_sensor": "המתנה לחיישן",

    # Safety Tab - Sensor condition values
    "active": "פעיל",
    "not_active": "לא פעיל",
    "Move to absolute position (both axes)": "תנועה למיקום מוחלט (שני הצירים)",

    # Safety Tab - Direction names (lowercase)
    "left": "שמאל",
    "right": "ימין",
    "top": "עליון",
    "bottom": "תחתון",
    "all_directions": "כל הכיוונים",

    # Safety Tab - Source Names (for condition display)
    "row_marker": "סמן עמודות",
    "row_cutter": "חותך עמודות",
    "line_motor": "מנוע שורות",
    "row_motor_limit_switch": "מתג גבול מנוע עמודות",
    "row_marker_up_sensor": "חיישן סמן עמודות למעלה",
    "row_marker_down_sensor": "חיישן סמן עמודות למטה",
    "row_cutter_up_sensor": "חיישן חותך עמודות למעלה",
    "row_cutter_down_sensor": "חיישן חותך עמודות למטה",
    "line_marker_up_sensor": "חיישן סמן שורות למעלה",
    "line_marker_down_sensor": "חיישן סמן שורות למטה",
    "line_cutter_up_sensor": "חיישן חותך שורות למעלה",
    "line_cutter_down_sensor": "חיישן חותך שורות למטה",
    "line_motor_left_up_sensor": "חיישן מנוע שורות שמאל למעלה",
    "line_motor_left_down_sensor": "חיישן מנוע שורות שמאל למטה",
    "line_motor_right_up_sensor": "חיישן מנוע שורות ימין למעלה",
    "line_motor_right_down_sensor": "חיישן מנוע שורות ימין למטה",
    "x_left_edge_sensor": "חיישן קצה שמאלי",
    "x_right_edge_sensor": "חיישן קצה ימני",
    "y_top_edge_sensor": "חיישן קצה עליון",
    "y_bottom_edge_sensor": "חיישן קצה תחתון",
    "x_position": "מיקום עמודות",
    "y_position": "מיקום שורות",
    "true": "כן",
    "false": "לא",

    # Config Tab - Section Titles
    "Hardware Limits": "מגבלות חומרה",
    "Timing Parameters": "פרמטרי זמן",
    "Hardware Configuration": "הגדרות חומרה",
    "Mock Hardware": "חומרה מדומה",
    "Logging Configuration": "הגדרות לוג",
    "GUI Settings": "הגדרות ממשק",
    "Hardware Monitor": "ניטור חומרה",
    "Operation Colors": "צבעי פעולות",
    "Sensor Timeouts": "זמני חיישנים",
    "Simulation": "סימולציה",
    "UI Fonts": "גופנים",
    "UI Spacing": "מרווחים",
    "Validation": "אימות",
    "Visualization": "ויזואליזציה",

    # Config Tab - Additional
    "Done": "הושלם",
    "Line Motor": "מנוע שורות",

    # ============================================================================
    # SETTINGS KEY TRANSLATIONS (for System Config tree leaf display)
    # ============================================================================

    # --- hardware_limits ---
    "max_x_position": "מיקום X מקסימלי",
    "max_y_position": "מיקום Y מקסימלי",
    "min_x_position": "מיקום X מינימלי",
    "min_y_position": "מיקום Y מינימלי",
    "paper_start_x": "התחלת נייר X",
    "paper_start_y": "התחלת נייר Y",
    "safe_movement_speed": "מהירות תנועה בטוחה",
    "max_acceleration": "תאוצה מקסימלית",
    "min_line_spacing": "מרווח שורות מינימלי",

    # --- admin ---
    "password": "סיסמה",

    # --- gui_settings ---
    "update_interval_ms": "תדירות עדכון (ms)",
    "auto_load_csv": "טעינת CSV אוטומטית",
    "canvas_margin_left": "שוליים שמאליים בקנבס",
    "canvas_margin_right": "שוליים ימניים בקנבס",
    "canvas_margin_top": "שוליים עליונים בקנבס",
    "canvas_margin_bottom": "שוליים תחתונים בקנבס",
    "canvas_min_scale": "סקאלה מינימלית בקנבס",

    # --- logging ---
    "level": "רמה",
    "show_timestamps": "הצג חותמות זמן",
    "show_thread_names": "הצג שמות תהליכונים",
    "console_output": "פלט לקונסולה",
    "file_output": "פלט לקובץ",
    "file_path": "נתיב קובץ",
    "use_colors": "השתמש בצבעים",
    "use_icons": "השתמש באייקונים",
    "queue_timeout_seconds": "זמן המתנה לתור (שניות)",
    "categories": "קטגוריות",
    "hardware": "חומרה",
    "execution": "ביצוע",
    "gui": "ממשק משתמש",

    # --- simulation ---
    "show_grid": "הצג רשת",
    "grid_spacing": "מרווח רשת",
    "max_display_x": "תצוגה מקסימלית X",
    "max_display_y": "תצוגה מקסימלית Y",

    # --- validation ---
    "tolerance": "סובלנות",
    "strict_mode": "מצב קפדני",

    # --- operation_colors ---
    "pending": "ממתין",
    "in_progress": "בביצוע",
    "completed": "הושלם",
    "mark": "סימון",
    "cuts": "חיתוך",

    # --- timing ---
    "motor_movement_delay_per_cm": "השהיית תנועה לס״מ",
    "max_motor_movement_delay": "השהיית תנועה מקסימלית",
    "tool_action_delay": "השהיית פעולת כלי",
    "sensor_poll_timeout": "זמן דגימת חיישן",
    "row_marker_stable_delay": "השהיית ייצוב סמן עמודות",
    "safety_check_interval": "תדירות בדיקת בטיחות",
    "execution_loop_delay": "השהיית לולאת ביצוע",
    "transition_monitor_interval": "תדירות ניטור מעברים",
    "thread_join_timeout_execution": "זמן המתנה לתהליכון ביצוע",
    "thread_join_timeout_safety": "זמן המתנה לתהליכון בטיחות",
    "sensor_wait_timeout": "זמן המתנה לחיישן",
    "piston_gpio_settling_delay": "השהיית ייצוב GPIO בוכנה",
    "gpio_cleanup_delay": "השהיית ניקוי GPIO",
    "gpio_busy_recovery_delay": "השהיית התאוששות GPIO",
    "gpio_debounce_samples": "דגימות ניפוי רעש GPIO",
    "gpio_debounce_delay_ms": "השהיית ניפוי רעש GPIO",
    "gpio_test_read_delay_ms": "השהיית קריאת בדיקה GPIO",
    "limit_switch_test_read_delay_ms": "השהיית קריאת מתג גבול",
    "polling_thread_join_timeout": "זמן המתנה לתהליכון דגימה",
    "switch_polling_interval_ms": "תדירות דגימת מתגים",
    "polling_status_update_frequency": "תדירות עדכון סטטוס דגימה",
    "polling_error_recovery_delay": "השהיית התאוששות שגיאת דגימה",
    "grbl_initialization_delay": "השהיית אתחול GRBL",
    "grbl_serial_poll_delay": "השהיית דגימה סריאלית GRBL",
    "grbl_reset_delay": "השהיית איפוס GRBL",
    "rs485_retry_delay": "השהיית ניסיון חוזר RS485",
    "grbl_init_delay": "השהיית אתחול GRBL",
    "grbl_operation_delay": "השהיית פעולה GRBL",
    "grbl_post_config_delay": "השהיה לאחר הגדרת GRBL",
    "homing_poll_interval": "תדירות דגימת ביות",
    "piston_full_operation_time": "זמן פעולת בוכנה מלאה",
    "tool_positioning_delay": "השהיית מיקום כלי",

    # --- sensor_timeouts ---
    "sensor_override_timeout_rows": "זמן עקיפת חיישן עמודות",
    "sensor_override_timeout_lines": "זמן עקיפת חיישן שורות",
    "sensor_highlight_duration": "משך הדגשת חיישן",

    # --- visualization ---
    "line_width_marks": "עובי קו סימון",
    "line_width_cuts": "עובי קו חיתוך",
    "dash_pattern_pending": "תבנית קו ממתין",
    "dash_pattern_in_progress": "תבנית קו בביצוע",
    "dash_pattern_completed": "תבנית קו הושלם",
    "sensor_indicator_size": "גודל מחוון חיישן",
    "sensor_highlight_color": "צבע הדגשת חיישן",
    "sensor_highlight_outline": "מסגרת הדגשת חיישן",
    "sensor_highlight_width": "עובי הדגשת חיישן",
    "motor_line_color_x": "צבע קו מנוע X",
    "motor_line_color_y": "צבע קו מנוע Y",
    "motor_intersection_size": "גודל צומת מנועים",

    # --- ui_fonts ---
    "title": "כותרת",
    "heading": "כותרת משנה",
    "normal": "רגיל",
    "dialog_title": "כותרת דיאלוג",
    "dialog_message": "הודעת דיאלוג",
    "dialog_label": "תווית דיאלוג",

    # --- ui_spacing ---
    "frame_padding": "ריפוד מסגרת",
    "widget_padding": "ריפוד רכיב",
    "dialog_padding": "ריפוד דיאלוג",
    "button_padding_x": "ריפוד כפתור אופקי",
    "button_padding_y": "ריפוד כפתור אנכי",

    # --- hardware_monitor ---
    "background_color": "צבע רקע",
    "section_bg_color": "צבע רקע מדור",
    "text_color": "צבע טקסט",
    "label_color": "צבע תווית",
    "separator_color": "צבע מפריד",
    "panel_height": "גובה פנל",
    "status_colors": "צבעי סטטוס",
    "motor_x": "מנוע X",
    "motor_y": "מנוע Y",
    "line_tools": "כלי שורות",
    "row_tools": "כלי עמודות",
    "sensors_x": "חיישני X",
    "sensors_y": "חיישני Y",
    "system": "מערכת",
    "inactive": "לא פעיל",
    "sensor_triggered_x": "חיישן X מופעל",
    "sensor_triggered_y": "חיישן Y מופעל",

    # --- hardware_config ---
    "use_real_hardware": "שימוש בחומרה אמיתית",
    "start_with_grbl": "התחל עם GRBL",
    "poc_mode": "מצב POC",
    "skip_initial_sensor_tests": "דלג על בדיקות חיישנים",
    "gpio_mode": "מצב GPIO",
    "debounce_count": "מספר ניפוי רעש",

    # --- hardware_config > pistons ---
    "line_marker_piston": "בוכנת סמן שורות",
    "line_cutter_piston": "בוכנת חותך שורות",
    "row_marker_piston": "בוכנת סמן עמודות",
    "row_cutter_piston": "בוכנת חותך עמודות",
    "air_pressure_valve": "שסתום לחץ אוויר",

    # --- hardware_config > rs485 ---
    "enabled": "מופעל",
    "serial_port": "פורט סריאלי",
    "baudrate": "קצב באוד",
    "bytesize": "גודל בית",
    "parity": "זוגיות",
    "stopbits": "סיביות עצירה",
    "timeout": "זמן המתנה",
    "protocol": "פרוטוקול",
    "modbus_device_id": "מזהה התקן Modbus",
    "modbus_function_code": "קוד פונקציית Modbus",
    "input_count": "מספר כניסות",
    "bulk_read_enabled": "קריאה מרוכזת מופעלת",
    "bulk_read_cache_age_ms": "גיל מטמון קריאה מרוכזת",
    "default_retry_count": "מספר ניסיונות חוזרים",
    "register_address_low": "כתובת רגיסטר תחתונה",
    "bulk_read_register_count": "מספר רגיסטרים לקריאה",
    "register_address": "כתובת רגיסטר",
    "sensor_addresses": "כתובות חיישנים",
    "nc_sensors": "חיישני NC",
    "x_left_edge": "קצה שמאלי X",
    "x_right_edge": "קצה ימני X",
    "y_top_edge": "קצה עליון Y",
    "y_bottom_edge": "קצה תחתון Y",

    # --- hardware_config > arduino_grbl ---
    "baud_rate": "קצב באוד",
    "connection_timeout": "זמן המתנה לחיבור",
    "command_timeout": "זמן המתנה לפקודה",
    "homing_timeout": "זמן המתנה לביות",
    "position_tolerance_cm": "סובלנות מיקום",
    "movement_timeout": "זמן המתנה לתנועה",
    "movement_poll_interval": "תדירות דגימת תנועה",

    # --- grbl_settings ---
    "units": "יחידות",
    "positioning_mode": "מצב מיקום",
    "feed_rate": "קצב הזנה",
    "rapid_rate": "קצב מהיר",

    # --- grbl_configuration ---
    "$0": "דופק צעד ($0)",
    "$1": "השהיית מנוחה ($1)",
    "$2": "היפוך פורט צעד ($2)",
    "$3": "היפוך פורט כיוון ($3)",
    "$4": "היפוך אפשור צעד ($4)",
    "$5": "היפוך פיני גבול ($5)",
    "$6": "היפוך פין בדיקה ($6)",
    "$10": "דוח סטטוס ($10)",
    "$11": "סטיית צומת ($11)",
    "$12": "סובלנות קשת ($12)",
    "$13": "דיווח באינצ׳ים ($13)",
    "$20": "גבולות רכים ($20)",
    "$21": "גבולות קשיחים ($21)",
    "$22": "מחזור ביות ($22)",
    "$23": "היפוך כיוון ביות ($23)",
    "$24": "קצב הזנת ביות ($24)",
    "$25": "קצב חיפוש ביות ($25)",
    "$26": "ניפוי רעש ביות ($26)",
    "$27": "מרחק התנתקות ביות ($27)",
    "$30": "מהירות ציר מקסימלית ($30)",
    "$31": "מהירות ציר מינימלית ($31)",
    "$32": "מצב לייזר ($32)",
    "$100": "צעדים/מ״מ X ($100)",
    "$101": "צעדים/מ״מ Y ($101)",
    "$102": "צעדים/מ״מ Z ($102)",
    "$110": "קצב מקסימלי X ($110)",
    "$111": "קצב מקסימלי Y ($111)",
    "$112": "קצב מקסימלי Z ($112)",
    "$120": "תאוצה X ($120)",
    "$121": "תאוצה Y ($121)",
    "$122": "תאוצה Z ($122)",
    "$130": "נסיעה מקסימלית X ($130)",
    "$131": "נסיעה מקסימלית Y ($131)",
    "$132": "נסיעה מקסימלית Z ($132)",

    "door": "דלת",
    "pin": "פין",
    "type": "סוג",
    "pull_up": "נגד עילי",
    "grbl_settings": "הגדרות GRBL",
    "grbl_configuration": "הגדרות GRBL מתקדמות",
    "pistons": "בוכנות",
    "rs485": "RS485",
    "raspberry_pi": "Raspberry Pi",
    "arduino_grbl": "Arduino GRBL",

    # --- section keys (top-level settings.json sections) ---
    "language": "שפה",
    "admin": "מנהל",
    "gui_settings": "הגדרות ממשק",
    "hardware_limits": "מגבלות חומרה",
    "hardware_config": "הגדרות חומרה",
    "hardware_monitor": "ניטור חומרה",
    "logging": "הגדרות לוג",
    "mock_hardware": "חומרה מדומה",
    "operation_colors": "צבעי פעולות",
    "sensor_timeouts": "זמני חיישנים",
    "simulation": "סימולציה",
    "timing": "פרמטרי זמן",
    "ui_fonts": "גופנים",
    "ui_spacing": "מרווחים",
    "validation": "אימות",
    "visualization": "ויזואליזציה",
    "grbl": "GRBL",

    # --- additional leaf keys ---
    "acceleration": "תאוצה",
    "door_sensor": "חיישן דלת",
    "label": "תווית",

    # --- mock_hardware ---
    "homing_step_delay": "השהיית צעד ביות",
    "door_check_delay": "השהיית בדיקת דלת",
    "piston_operation_delay": "השהיית פעולת בוכנה",
    "grbl_homing_delay": "השהיית ביות GRBL",
    "coordinate_reset_delay": "השהיית איפוס קואורדינטות",

    # ============================================================================
    # ANALYTICS TAB
    # ============================================================================
    "Analytics": "אנליטיקה",

    # Summary labels
    "Summary": "סיכום",
    "Total Runs": "סה\"כ הרצות",
    "Success Rate": "אחוז הצלחה",
    "Successful": "הצליחו",
    "User Stopped": "עצירת משתמש",
    "Safety Violations": "הפרות בטיחות",
    "Emergency Stops": "עצירות חירום",
    "Errors": "שגיאות",
    "Avg Duration": "משך ממוצע",
    "Most Run Program": "תוכנית שרצה הכי הרבה",
    "Common Safety Code": "קוד בטיחות נפוץ",

    # Table headers
    "Execution History": "היסטוריית הרצות",
    "Date/Time": "תאריך/שעה",
    "Program": "תוכנית",
    "Status": "סטטוס",
    "Duration": "משך",
    "Steps": "צעדים",
    "Info": "מידע",

    # Filters and actions
    "Date From:": "מתאריך:",
    "Date To:": "עד תאריך:",
    "Export CSV": "ייצוא CSV",
    "Clear Data": "נקה נתונים",
    "Delete all analytics data? This cannot be undone.": "למחוק את כל נתוני האנליטיקה? פעולה זו אינה הפיכה.",
    "No Data": "אין נתונים",
    "No data to export": "אין נתונים לייצוא",
    "Data exported to {filename}": "נתונים יוצאו ל-{filename}",
    "Analytics exported to {filename}": "אנליטיקה יוצאה ל-{filename}",
    "Analytics data cleared": "נתוני אנליטיקה נוקו",
    "Failed to load analytics: {error}": "כשלון בטעינת אנליטיקה: {error}",

    # Run details popup
    "Run Details": "פרטי הרצה",

    # Email Reports section
    "Email Reports": "דוחות מייל",
    "SMTP Server:": "שרת SMTP:",
    "Port:": "פורט:",
    "Username:": "שם משתמש:",
    "Password:": "סיסמה:",
    "Sender Email:": "מייל שולח:",
    "Recipient Email:": "מייל נמען:",
    "Subject Prefix:": "קידומת נושא:",
    "Enable Email": "הפעל מייל",
    "Schedule Enabled": "תזמון מופעל",
    "Interval (hours):": "מרווח (שעות):",
    "Send Time:": "שעת שליחה:",
    "Test Connection": "בדוק חיבור",
    "Testing...": "בודק...",
    "Connection OK!": "החיבור תקין!",
    "Auth failed - check App Password": "אימות נכשל - בדוק סיסמת אפליקציה",
    "Cannot connect to server": "לא ניתן להתחבר לשרת",
    "Fill server, username & password": "מלא שרת, שם משתמש וסיסמה",
    "SMTP connection test passed": "בדיקת חיבור SMTP עברה בהצלחה",
    "Email scheduler started": "תזמון מייל הופעל",
    "Email scheduler stopped": "תזמון מייל הופסק",
    "Send Report Now": "שלח דוח עכשיו",
    "Save Email Settings": "שמור הגדרות מייל",
    "Settings saved": "ההגדרות נשמרו",
    "Email settings saved": "הגדרות מייל נשמרו",
    "Sending...": "שולח...",
    "Report sent!": "הדוח נשלח!",
    "Analytics report sent": "דוח אנליטיקה נשלח",
    "Failed: {error}": "נכשל: {error}",
    "Report send failed: {error}": "שליחת דוח נכשלה: {error}",
    "Error: {error}": "שגיאה: {error}",
    "Last sent: Never": "נשלח לאחרונה: מעולם לא",
    "Last sent: {time}": "נשלח לאחרונה: {time}",

    # Analytics settings keys
    "analytics": "אנליטיקה",
    "csv_file_path": "נתיב קובץ CSV",
    "email": "מייל",
    "smtp_server": "שרת SMTP",
    "smtp_port": "פורט SMTP",
    "smtp_use_tls": "שימוש ב-TLS",
    "smtp_username": "שם משתמש SMTP",
    "smtp_password": "סיסמת SMTP",
    "sender_email": "מייל שולח",
    "recipient_email": "מייל נמען",
    "subject_prefix": "קידומת נושא",
    "schedule_enabled": "תזמון מופעל",
    "schedule_frequency": "תדירות שליחה",
    "schedule_time": "שעת שליחה",
    "schedule_day_of_week": "יום בשבוע",
    "schedule_day_of_month": "יום בחודש",
    "last_sent": "נשלח לאחרונה",
    "Frequency:": "תדירות:",
    "Send Time (HH:MM):": "שעת שליחה (HH:MM):",
    "Day of Week:": "יום בשבוע:",
    "Day of Month:": "יום בחודש:",
    "Monday": "יום שני",
    "Tuesday": "יום שלישי",
    "Wednesday": "יום רביעי",
    "Thursday": "יום חמישי",
    "Friday": "יום שישי",
    "Saturday": "שבת",
    "Sunday": "יום ראשון",
}

# Current language setting
_current_language = "he"  # Default to Hebrew

def set_language(lang_code):
    """
    Set the current language

    Args:
        lang_code: Language code ("he" for Hebrew, "en" for English)
    """
    global _current_language
    _current_language = lang_code

def get_language():
    """Get the current language code"""
    return _current_language

def _apply_bidi(text):
    """Convert Hebrew text from logical to visual order on Linux (Xft)."""
    if not _NEEDS_BIDI_REORDER or _bidi_get_display is None:
        return text
    if not text or not isinstance(text, str):
        return text
    # Process multi-line text line by line
    if '\n' in text:
        return '\n'.join(_apply_bidi(line) for line in text.split('\n'))
    return _bidi_get_display(text)

def t(text, **kwargs):
    """
    Translate text to Hebrew with proper RTL display formatting

    Args:
        text: English text to translate
        **kwargs: Format arguments for f-string style formatting

    Returns:
        Translated text with RTL formatting (or original if translation not found)

    Examples:
        t("Connect Hardware")  # Returns: "התחבר לחומרה" (with RTL formatting)
        t("X: {x:.2f} cm", x=5.5)  # Returns: "X: 5.50 ס״מ" (with RTL formatting)
    """
    # If language is English, return original
    if _current_language == "en":
        if kwargs:
            return text.format(**kwargs)
        return text

    # Get Hebrew translation
    translated = HEBREW_TRANSLATIONS.get(text, text)

    # Apply formatting if kwargs provided
    if kwargs:
        try:
            translated = translated.format(**kwargs)
        except (KeyError, ValueError) as e:
            # If formatting fails, return original with formatting
            print(f"Translation formatting error for '{text}': {e}")
            return text.format(**kwargs)

    return _apply_bidi(translated)

def t_title(text: str, **kwargs) -> str:
    """Translate text for use as a Tkinter window title with RTL support.

    Window titles are rendered by the window manager, not Tkinter's Xft,
    so BiDi reordering doesn't apply. Instead, prepend the Unicode RTL Mark
    (U+200F) so the WM renders the title right-to-left.
    """
    translated = t(text, **kwargs)
    if _current_language != "en" and translated:
        return '\u200f' + str(translated)
    return str(translated)

def rtl_title(text: str) -> str:
    """Prepend RTL mark to an already-Hebrew string for use as a window title."""
    if _current_language != "en" and text:
        return '\u200f' + text
    return text

def rtl(text):
    """Apply BiDi visual reordering to pre-translated Hebrew text.

    For Hebrew strings not from HEBREW_TRANSLATIONS (e.g., hebDescription
    from step_generator). On macOS/Windows, returns text unchanged.
    """
    return _apply_bidi(text)

def load_language_from_config():
    """
    Load language preference from settings.json

    Returns:
        Language code from config or 'he' as default
    """
    try:
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'settings.json')
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                lang = config.get('language', 'he')
                set_language(lang)
                return lang
    except Exception as e:
        print(f"Error loading language from config: {e}")

    return 'he'  # Default to Hebrew

# Initialize language from config on module import
load_language_from_config()
