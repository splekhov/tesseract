#!/usr/bin/env python3
import datetime
import calendar

# Monday-first, like `cal -m`
calendar.setfirstweekday(calendar.MONDAY)

WIDTH = 20
SEP = "  "

# ANSI reverse-video for highlighting
HL_START = "\x1b[7m"
HL_END = "\x1b[0m"

today = datetime.date.today()


def month_block(year, month):
    cal = calendar.Calendar(firstweekday=calendar.MONDAY)
    weeks = cal.monthdayscalendar(year, month)

    header = f"{calendar.month_name[month]} {year}".center(WIDTH)
    weekdays = "Mo Tu We Th Fr Sa Su"

    lines = [header, weekdays]

    for w in weeks:
        parts = []
        for d in w:
            if d == 0:
                parts.append("  ")
            else:
                if year == today.year and month == today.month and d == today.day:
                    # Highlight current day
                    parts.append(f"{HL_START}{d:2d}{HL_END}")
                else:
                    parts.append(f"{d:2d}")
        lines.append(" ".join(parts))

    while len(lines) < 8:
        lines.append(" " * WIDTH)

    return lines


def main():
    y, m = today.year, today.month

    # previous month
    if m == 1:
        prev_y, prev_m = y - 1, 12
    else:
        prev_y, prev_m = y, m - 1

    # next month
    if m == 12:
        next_y, next_m = y + 1, 1
    else:
        next_y, next_m = y, m + 1

    prev_block = month_block(prev_y, prev_m)
    curr_block = month_block(y, m)
    next_block = month_block(next_y, next_m)

    for i in range(8):
        print(prev_block[i] + SEP + curr_block[i] + SEP + next_block[i])


if __name__ == "__main__":
    main()

