# NTU ICPC Scoreboards

A tool for hosting live scoreboards and organizing practice contest results for the NTU ICPC Class.

## Requirements

Install the Python dependencies:

```bash
pip install -r requirements.txt
```

System dependencies:

- Chrome or Chromium
- `xvfb-run`

## Run the Server

```bash
python app.py <port>
```

The default port is `5000`.

## Teams

Team information must be stored in `teams/teams.json`. The following is an example entry:

```json
{
    "teamname": "std_abs",
    "qoj-name": "std_abs",
    "qoj-username": "std_abs",
    "codeforces-team-id": [108680]
}
```

The fields have the following meanings:

- `teamname`: the name used to identify and display the team.
- `qoj-name`: the team's display name on QOJ.
- `qoj-username`: the team's QOJ username.
- `codeforces-team-id`: the team's Codeforces team ID. Multiple team IDs are supported.

## Live Scoreboard

Two platforms are currently supported: Codeforces and QOJ. The tool downloads and filters the standings every 60 seconds, then displays the result at `/live`.

### Codeforces

```bash
python live/live.py codeforces <scoreboard_link>
```

- Contests hosted in a Codeforces group are recommended. Regular contests and gyms may not display correctly because of unofficial participation or limits on the number of teams shown in the standings.

### QOJ

```bash
python live/live.py qoj <scoreboard_link> <start_time> <id_l> <id_r>
```

- `scoreboard_link` must point to an External Standings page, such as `https://qoj.ac/results/QOJ3747`.
- `start_time` must use ISO 8601 format, such as `2026-08-12T18:25:00`. If no timezone is provided, UTC+8 is used by default. You may also specify an offset explicitly, such as `2026-08-12T18:25:00+08:00`. The QOJ live scoreboard freezes four hours after the contest starts and unfreezes after five hours.
- `id_l` and `id_r` are the first and last QOJ problem IDs for the contest. The tool assumes that all problem IDs in the contest are consecutive.

## Tools

### Stop the Live Scoreboard

After the contest ends, disable the live scoreboard with:

```bash
python tools/stop-live.py
```

### Archive a Scoreboard

```bash
python tools/archive.py codeforces <archive_id> <title> <html>
python tools/archive.py qoj <archive_id> <title> <html> <id_l> <id_r>
python tools/archive.py live <archive_id> <title>
```

- Use the `YYYYMMDD` format for `archive_id` so that yearly statistics are displayed correctly.
- When archiving Codeforces or QOJ standings, first save the standings page as an HTML file, then pass the file path through the `html` argument.
- For QOJ, `id_l` and `id_r` are the first and last problem IDs. The tool assumes that all problem IDs in the contest are consecutive.
- `title` is the title displayed on the archived scoreboard.

### Build Ratings

Creating an archive does not automatically generate its ratings. To create rating,

```bash
python tools/build-rating.py <archive_id>
```

### Build an Upsolve Scoreboard

This feature currently supports QOJ archives only.

QOJ user profile pages cannot be downloaded easily by a crawler, so each profile must be saved manually in the `teams/` directory. The filename must be `<qoj_username>.html`, for example `std_abs.html`.

Use `tools/open-team-profiles.py` to open every team's QOJ profile in your browser. Then run the JavaScript from `tools/download-user-page.js` in the browser's developer console to download each page as an HTML file.

After saving all profile pages, run:

```bash
python tools/build-upsolve.py <archive_id>
```
