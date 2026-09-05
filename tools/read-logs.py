#!/usr/bin/env python3
"""Report visits vs click-throughs from an Amplify access-log CSV.

    python3 tools/read-logs.py access-logs.csv
    python3 tools/read-logs.py access-logs.csv --hours     # add time-of-day

Get the CSV from: Amplify console -> your landing app -> Hosting -> Monitoring
-> Access logs -> pick a date range -> Download.

Same parsing as the /usage page, via tools/logs.py.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import logs


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    try:
        data = logs.read(argv[1])
    except logs.LayoutError as e:
        print('Could not find the time and path columns. Headers were:')
        for h in e.headers:
            print('   ', h)
        sys.exit('\nSend me this header line and I will teach the parser the layout.')

    days, totals = data['days'], data['totals']
    if not totals:
        sys.exit('No page or /go requests found - is this the right log file?')

    print(f'\n{"day":<12}{"visits":>8}{"clicks":>8}{"rate":>8}')
    print('-' * 36)
    for day in sorted(days):
        v, c = days[day].get('visit', 0), days[day].get('click', 0)
        rate = f'{round(100 * c / v)}%' if v else '-'
        print(f'{day:<12}{v:>8}{c:>8}{rate:>8}')
    print('-' * 36)
    v, c = totals['visit'], totals['click']
    print(f'{"TOTAL":<12}{v:>8}{c:>8}{(f"{round(100 * c / v)}%" if v else "-"):>8}')
    if data['bots']:
        print(f'\n({data["bots"]} bot/preview requests excluded)')

    if '--hours' in argv and data['hours']:
        hours = data['hours']
        print('\nclicks by hour (UTC)')
        peak = max(hours.values())
        for h in range(24):
            n = hours.get(h, 0)
            bar = '#' * round(18 * n / peak) if n else ''
            print(f'  {h:02d}:00 {n:>4} {bar}')

    print('\nRequests are not people: reloads count twice, and the ratio is the')
    print('trustworthy number rather than either total on its own.')


if __name__ == '__main__':
    main(sys.argv)
