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
    "X: {x:.2f} cm": "X: {x:.2f} ס״מ",
    "Y: {y:.2f} cm": "Y: {y:.2f} ס״מ",
    "Status:": "סטטוס:",
    "Idle": "מנוח",
    "Jog Control": "בקרת תנועה",
    "Step Size:": "גודל צעד:",
    "0.1mm": "0.1 מ״מ",
    "1mm": "1 מ״מ",
    "10mm": "10 מ״מ",
    "100mm": "100 מ״מ",
    "Y+↑": "↑Y+",
    "←X-": "X-←",
    "HOME": "בית",
    "X+→": "→X+",
    "↓Y-": "Y-↓",
    "Go to Position": "עבור למיקום",
    "X (cm):": ":(ס״מ) X",
    "Y (cm):": ":(ס״מ) Y",
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
    "Rows Limit": "גבול שורות",
    "OPEN": "פתוח",
    "CLOSED": "סגור",

    # ============================================================================
    # HARDWARE TEST GUI - Pistons Tab
    # ============================================================================
    "Piston Control": "בקרת בוכנות",
    "Line Marker": "סמן קווים",
    "Line Cutter": "חותך קווים",
    "Line Motor (Both)": "מנוע קווים (שניהם)",
    "Row Marker": "סמן שורות",
    "Row Cutter": "חותך שורות",
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
    "X Left Edge": "קצה שמאלי X",
    "X Right Edge": "קצה ימני X",
    "Y Top Edge": "קצה עליון Y",
    "Y Bottom Edge": "קצה תחתון Y",

    # ============================================================================
    # HARDWARE TEST GUI - GRBL Tab
    # ============================================================================
    "Read Settings ($$)": "קרא הגדרות ($$)",
    "Apply Changes": "החל שינויים",
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

    "Steps per mm for X axis": "צעדים למ״מ עבור ציר X",
    "Steps per mm for Y axis": "צעדים למ״מ עבור ציר Y",
    "Steps per mm for Z axis": "צעדים למ״מ עבור ציר Z",
    "Maximum rate for X axis (mm/min)": "קצב מקסימלי עבור ציר X (מ״מ/דקה)",
    "Maximum rate for Y axis (mm/min)": "קצב מקסימלי עבור ציר Y (מ״מ/דקה)",
    "Maximum rate for Z axis (mm/min)": "קצב מקסימלי עבור ציר Z (מ״מ/דקה)",
    "X axis acceleration (mm/sec²)": "תאוצת ציר X (מ״מ/שנייה²)",
    "Y axis acceleration (mm/sec²)": "תאוצת ציר Y (מ״מ/שנייה²)",
    "Z axis acceleration (mm/sec²)": "תאוצת ציר Z (מ״מ/שנייה²)",
    "X axis maximum travel (mm)": "מרחק נסיעה מקסימלי ציר X (מ״מ)",
    "Y axis maximum travel (mm)": "מרחק נסיעה מקסימלי ציר Y (מ״מ)",
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
    "High (cm):": ":(ס״מ) גובה",
    "Number of Lines:": ":מספר קווים",
    "Top Margin (cm):": ":(ס״מ) שוליים עליונים",
    "Bottom Margin (cm):": ":(ס״מ) שוליים תחתונים",
    "Width (cm):": ":(ס״מ) רוחב",
    "Left Margin (cm):": ":(ס״מ) שוליים שמאליים",
    "Right Margin (cm):": ":(ס״מ) שוליים ימניים",
    "Page Width (cm):": ":(ס״מ) רוחב עמוד",
    "Number of Pages:": ":מספר עמודים",
    "Buffer Between Pages (cm):": ":(ס״מ) מרווח בין עמודים",
    "Repeat Rows:": ":חזרה על שורות",
    "Repeat Lines:": ":חזרה על קווים",
    "Update Program": "עדכן תוכנית",
    "Validate": "אמת",
    "No program selected": "לא נבחרה תוכנית",
    "Program is valid": "התוכנית תקינה",

    # Paper Size Section
    "📐 ACTUAL PAPER SIZE (With Repeats)": "📐 גודל נייר בפועל (עם חזרות)",
    "Single Pattern:": ":תבנית בודדת",
    "{w:.1f} × {h:.1f} cm": "{w:.1f} × {h:.1f} ס״מ",
    "Repeats:": ":חזרות",
    "{rows} rows × {lines} lines": "{rows} שורות × {lines} קווים",
    "🎯 ACTUAL SIZE NEEDED:": ":🎯 גודל נדרש בפועל",
    "{w:.1f} × {h:.1f} cm": "{w:.1f} × {h:.1f} ס״מ",
    "✅ Fits on desk": "✅ מתאים לשולחן",
    "⚠️ Width exceeds desk": "⚠️ רוחב חורג מהשולחן",
    "⚠️ Height exceeds desk": "⚠️ גובה חורג מהשולחן",
    "⚠️ Exceeds desk size": "⚠️ חורג מגודל השולחן",

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
    "Step Navigation:": ":ניווט צעדים",
    "◄ Prev": "◄ הקודם",
    "Next ►": "הבא ►",
    "No steps loaded": "לא נטענו צעדים",
    "Steps Queue:": ":תור צעדים",
    "Current": "נוכחי",
    "All Steps": "כל הצעדים",
    "No step selected": "לא נבחר צעד",
    "Selected Step Details:": ":פרטי צעד נבחר",
    "Click on a step to view details...": "...לחץ על צעד כדי להציג פרטים",
    "Execution:": ":ביצוע",
    "▶ RUN": "▶ הפעל",
    "⏸ PAUSE": "⏸ השהה",
    "⏹ STOP": "⏹ עצור",
    "🔄 RESET": "🔄 אפס",
    "Ready": "מוכן",

    # Test Controls
    "🧪 TEST CONTROLS": "🧪 בקרות בדיקה",
    "📡 Sensors": "📡 חיישנים",
    "X:": ":X",
    "Y:": ":Y",
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
    "Lines:": ":קווים",
    "Rows:": ":שורות",
    "Marker": "סמן",
    "Cutter": "חותך",
    "Motor": "מנוע",

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
    "✏️ LINES": "✏️ קווים",
    "✂️ ROWS": "✂️ שורות",
    "Tool Sensors": "חיישני כלי",
    "Edge Sensors": "חיישני קצה",
    "Pistons": "בוכנות",
    "X Position": "מיקום X",
    "Y Position": "מיקום Y",
    "Top Limit Switch": "מתג גבול עליון",
    "Bottom Limit Switch": "מתג גבול תחתון",
    "Right Limit Switch": "מתג גבול ימני",
    "Left Limit Switch": "מתג גבול שמאלי",
    "Rows Limit Switch": "מתג גבול שורות",
    "Marker ↑": "סמן ↑",
    "Marker ↓": "סמן ↓",
    "Cutter ↑": "חותך ↑",
    "Cutter ↓": "חותך ↓",
    "Motor L↑": "מנוע ש↑",
    "Motor L↓": "מנוע ש↓",
    "Motor R↑": "מנוע י↑",
    "Motor R↓": "מנוע י↓",
    "X Left": "X שמאל",
    "X Right": "X ימין",
    "Y Top": "Y עליון",
    "Y Bottom": "Y תחתון",
    "Mode:": ":מצב",
    "IDLE": "מנוח",
    "System ready": "המערכת מוכנה",
    "Progress:": ":התקדמות",
    "OFF": "כבוי",
    "ON": "פעיל",
    "TRIG": "מופעל",
    "READY": "מוכן",
    "UP": "למעלה",
    "DOWN": "למטה",

    # Operation Modes
    "BLOCKED": "חסום",
    "Waiting": "ממתין",
    "LINES": "קווים",
    "Marking lines": "מסמן קווים",
    "ROWS": "שורות",
    "Cutting rows": "חותך שורות",
    "System ready": "המערכת מוכנה",
    "SUCCESS": "הצלחה",
    "All done!": "!הכל הושלם",
    "FAIL": "כישלון",
    "Not completed": "לא הושלם",

    # ============================================================================
    # HARDWARE SETTINGS PANEL
    # ============================================================================
    "⚙️ Hardware Settings": "⚙️ הגדרות חומרה",
    "Hardware Mode:": ":מצב חומרה",
    "🖥️ Simulation": "🖥️ סימולציה",
    "🔧 Real Hardware": "🔧 חומרה אמיתית",
    "Arduino Port:": ":פורט Arduino",
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
    "Error: {message}": "שגיאה: {message}",
    "Executing step...": "...מבצע צעד",
    "Waiting for {sensor} sensor": "ממתין לחיישן {sensor}",
    "{progress}% Complete ({step_index}/{total_steps} steps)": "{progress}% הושלם ({step_index}/{total_steps} צעדים)",
    "100% Complete - Execution finished": "100% הושלם - הביצוע הסתיים",
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
    "STATUS:": ":סטטוס",

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
    # STEP GENERATOR - Step Descriptions
    # ============================================================================
    # Motor initialization
    "Init: Move rows motor to home position (X=0)": "אתחול: הזז מנוע שורות למיקום בית (X=0)",
    "Init: Move lines motor to home position (Y=0)": "אתחול: הזז מנוע קווים למיקום בית (Y=0)",

    # Line motor piston movements
    "⚠️ Lifting line motor piston UP (preparing for upward movement to {pos}cm)": "⚠️ הרמת בוכנת מנוע קווים למעלה (הכנה לתנועה כלפי מעלה ל-{pos} ס״מ)",
    "Init: Move Y motor to {pos}cm (paper + {height}cm ACTUAL high)": "אתחול: הזז מנוע Y ל-{pos} ס״מ (נייר + {height} ס״מ גובה בפועל)",
    "Line motor piston DOWN (Y motor assembly lowered to default position)": "בוכנת מנוע קווים למטה (מכלול מנוע Y הורד למיקום ברירת המחדל)",

    # Cut edges - Lines
    "Cut top edge: Wait for LEFT X sensor": "חיתוך קצה עליון: המתן לחיישן X שמאלי",
    "Cut top edge: Open line cutter": "חיתוך קצה עליון: פתח חותך קווים",
    "Cut top edge: Wait for RIGHT X sensor": "חיתוך קצה עליון: המתן לחיישן X ימני",
    "Cut top edge: Close line cutter": "חיתוך קצה עליון: סגור חותך קווים",

    "Cut bottom edge: Wait for LEFT X sensor": "חיתוך קצה תחתון: המתן לחיישן X שמאלי",
    "Cut bottom edge: Open line cutter": "חיתוך קצה תחתון: פתח חותך קווים",
    "Cut bottom edge: Wait for RIGHT X sensor": "חיתוך קצה תחתון: המתן לחיישן X ימני",
    "Cut bottom edge: Close line cutter": "חיתוך קצה תחתון: סגור חותך קווים",

    # Line marking
    "Move to first line of section {section}: {pos}cm": "עבור לקו ראשון של חלק {section}: {pos} ס״מ",
    "Move to line position: {pos:.1f}cm": "עבור למיקום קו: {pos:.1f} ס״מ",
    "Mark line {num}/{total} (Section {section}, Line {line})": "סמן קו {num}/{total} (חלק {section}, קו {line})",
    "{desc}: Wait for LEFT X sensor": "{desc}: המתן לחיישן X שמאלי",
    "{desc}: Open line marker": "{desc}: פתח סמן קווים",
    "{desc}: Wait for RIGHT X sensor": "{desc}: המתן לחיישן X ימני",
    "{desc}: Close line marker": "{desc}: סגור סמן קווים",

    # Cut between sections
    "Move to cut between sections {sec1} and {sec2}: {pos}cm": "עבור לחיתוך בין חלקים {sec1} ו-{sec2}: {pos} ס״מ",
    "Cut between sections {sec1} and {sec2}: Wait for LEFT X sensor": "חיתוך בין חלקים {sec1} ו-{sec2}: המתן לחיישן X שמאלי",
    "Cut between sections {sec1} and {sec2}: Open line cutter": "חיתוך בין חלקים {sec1} ו-{sec2}: פתח חותך קווים",
    "Cut between sections {sec1} and {sec2}: Wait for RIGHT X sensor": "חיתוך בין חלקים {sec1} ו-{sec2}: המתן לחיישן X ימני",
    "Cut between sections {sec1} and {sec2}: Close line cutter": "חיתוך בין חלקים {sec1} ו-{sec2}: סגור חותך קווים",

    # Bottom position and completion
    "Move to bottom cut position: {pos}cm (paper starting position)": "עבור למיקום חיתוך תחתון: {pos} ס״מ (מיקום התחלת נייר)",
    "Lines complete: Move lines motor to home position (Y=0)": "קווים הושלמו: הזז מנוע קווים למיקום בית (Y=0)",

    # Rows operation
    "Rows operation: Ensure lines motor is at home position (Y=0)": "פעולת שורות: ודא שמנוע קווים במיקום בית (Y=0)",

    # Cut edges - Rows
    "Cut RIGHT paper edge: Move to {pos}cm (ACTUAL width)": "חיתוך קצה נייר ימני: עבור ל-{pos} ס״מ (רוחב בפועל)",
    "Cut RIGHT paper edge: Wait for TOP Y sensor": "חיתוך קצה נייר ימני: המתן לחיישן Y עליון",
    "Cut RIGHT paper edge: Open row cutter": "חיתוך קצה נייר ימני: פתח חותך שורות",
    "Cut RIGHT paper edge: Wait for BOTTOM Y sensor": "חיתוך קצה נייר ימני: המתן לחיישן Y תחתון",
    "Cut RIGHT paper edge: Close row cutter": "חיתוך קצה נייר ימני: סגור חותך שורות",

    "Cut LEFT paper edge: Move to {pos}cm (ACTUAL paper boundary)": "חיתוך קצה נייר שמאלי: עבור ל-{pos} ס״מ (גבול נייר בפועל)",
    "Cut LEFT paper edge: Wait for TOP Y sensor": "חיתוך קצה נייר שמאלי: המתן לחיישן Y עליון",
    "Cut LEFT paper edge: Open row cutter": "חיתוך קצה נייר שמאלי: פתח חותך שורות",
    "Cut LEFT paper edge: Wait for BOTTOM Y sensor": "חיתוך קצה נייר שמאלי: המתן לחיישן Y תחתון",
    "Cut LEFT paper edge: Close row cutter": "חיתוך קצה נייר שמאלי: סגור חותך שורות",

    # Page marking
    "RTL Page {num}/{total} (Section {section}, RTL Page {page}/{pages})": "עמוד RTL {num}/{total} (חלק {section}, עמוד RTL {page}/{pages})",
    "Move to {desc} RIGHT edge: {pos}cm": "עבור לקצה ימני של {desc}: {pos} ס״מ",
    "{desc}: Wait TOP Y sensor (RIGHT edge)": "{desc}: המתן לחיישן Y עליון (קצה ימני)",
    "{desc}: Open row marker (RIGHT edge)": "{desc}: פתח סמן שורות (קצה ימני)",
    "{desc}: Wait BOTTOM Y sensor (RIGHT edge)": "{desc}: המתן לחיישן Y תחתון (קצה ימני)",
    "{desc}: Close row marker (RIGHT edge)": "{desc}: סגור סמן שורות (קצה ימני)",

    "RTL: Move to {desc} LEFT edge: {pos}cm": "RTL: עבור לקצה שמאלי של {desc}: {pos} ס״מ",
    "{desc}: Wait TOP Y sensor (LEFT edge)": "{desc}: המתן לחיישן Y עליון (קצה שמאלי)",
    "{desc}: Open row marker (LEFT edge)": "{desc}: פתח סמן שורות (קצה שמאלי)",
    "{desc}: Wait BOTTOM Y sensor (LEFT edge)": "{desc}: המתן לחיישן Y תחתון (קצה שמאלי)",
    "{desc}: Close row marker (LEFT edge)": "{desc}: סגור סמן שורות (קצה שמאלי)",

    # Cut between row sections
    "Move to cut between row sections {sec1} and {sec2}: {pos}cm": "עבור לחיתוך בין חלקי שורות {sec1} ו-{sec2}: {pos} ס״מ",
    "Cut between row sections {sec1} and {sec2}: Wait for TOP Y sensor": "חיתוך בין חלקי שורות {sec1} ו-{sec2}: המתן לחיישן Y עליון",
    "Cut between row sections {sec1} and {sec2}: Open row cutter": "חיתוך בין חלקי שורות {sec1} ו-{sec2}: פתח חותך שורות",
    "Cut between row sections {sec1} and {sec2}: Wait for BOTTOM Y sensor": "חיתוך בין חלקי שורות {sec1} ו-{sec2}: המתן לחיישן Y תחתון",
    "Cut between row sections {sec1} and {sec2}: Close row cutter": "חיתוך בין חלקי שורות {sec1} ו-{sec2}: סגור חותך שורות",

    # Rows completion
    "Rows complete: Move rows motor to home position (X=0)": "שורות הושלמו: הזז מנוע שורות למיקום בית (X=0)",

    # Program start/complete
    "=== Starting Program {num}: {name} (ACTUAL SIZE: {width}×{height}cm) ===": "=== מתחיל תוכנית {num}: {name} (גודל בפועל: {width}×{height} ס״מ) ===",
    "=== Program {num} completed: {width}×{height}cm paper processed ===": "=== תוכנית {num} הושלמה: נייר {width}×{height} ס״מ עובד ===",
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

def t(text, **kwargs):
    """
    Translate text to Hebrew

    Args:
        text: English text to translate
        **kwargs: Format arguments for f-string style formatting

    Returns:
        Translated text (or original if translation not found)

    Examples:
        t("Connect Hardware")  # Returns: "התחבר לחומרה"
        t("X: {x:.2f} cm", x=5.5)  # Returns: "X: 5.50 ס״מ"
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

    return translated

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
