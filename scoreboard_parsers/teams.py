from pathlib import Path

from scoreboard_parsers.io import load_json


def load_teams(path):
    path = Path(path)
    teams = load_json(path)
    if not isinstance(teams, list):
        raise RuntimeError(f"Team configuration must be a JSON array: {path}")
    seen_teamnames = set()
    for index, team in enumerate(teams, start=1):
        if not isinstance(team, dict):
            raise RuntimeError(f"Team entry {index} must be an object")
        teamname = team.get("teamname")
        if not isinstance(teamname, str) or not teamname.strip():
            raise RuntimeError(f"Team entry {index} does not have a valid teamname")
        if teamname in seen_teamnames:
            raise RuntimeError(f"Duplicate teamname in teams.json: {teamname}")
        seen_teamnames.add(teamname)
    return teams


def qoj_name_map(path):
    result = {}
    for team in load_teams(path):
        qoj_name = team.get("qoj-name")
        if not isinstance(qoj_name, str) or not qoj_name.strip():
            continue
        if qoj_name in result:
            raise RuntimeError(f"Duplicate QOJ name in teams.json: {qoj_name}")
        result[qoj_name] = team["teamname"]
    if not result:
        raise RuntimeError(f"No QOJ team names found in {path}")
    return result


def qoj_username_map(path, require_all=False):
    result = {}
    usernames = set()
    for team in load_teams(path):
        username = team.get("qoj-username", "")
        if not isinstance(username, str):
            raise RuntimeError(f"Invalid QOJ username for team {team['teamname']!r}")
        username = username.strip()
        if not username:
            if require_all:
                raise RuntimeError(
                    f"Team {team['teamname']!r} does not have a QOJ username"
                )
            continue
        if username in usernames:
            raise RuntimeError(f"Duplicate QOJ username in teams.json: {username}")
        usernames.add(username)
        result[team["teamname"]] = username
    return result


def codeforces_team_id_map(path):
    result = {}
    for team in load_teams(path):
        team_ids = team.get("codeforces-team-id")
        if team_ids is None:
            continue
        if not isinstance(team_ids, list):
            team_ids = [team_ids]
        for raw_team_id in team_ids:
            team_id = int(raw_team_id)
            if team_id in result:
                raise RuntimeError(f"Duplicate Codeforces team ID: {team_id}")
            result[team_id] = team["teamname"]
    if not result:
        raise RuntimeError(f"No Codeforces team IDs found in {path}")
    return result
