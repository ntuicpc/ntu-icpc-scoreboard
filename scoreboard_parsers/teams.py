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
            raise RuntimeError(f"Duplicate teamname in {path}: {teamname}")
        seen_teamnames.add(teamname)
    return teams


def load_live_teams(official_path, unofficial_path):
    official_teams = load_teams(official_path)
    unofficial_teams = load_teams(unofficial_path)

    official_names = {team["teamname"] for team in official_teams}
    duplicate_names = sorted(
        official_names.intersection(
            team["teamname"] for team in unofficial_teams
        )
    )
    if duplicate_names:
        raise RuntimeError(
            "Teams cannot be both official and unofficial: "
            + ", ".join(duplicate_names)
        )

    return official_teams, unofficial_teams


def _qoj_name_map(teams, path, require_names=True):
    result = {}
    for team in teams:
        qoj_name = team.get("qoj-name")
        if not isinstance(qoj_name, str) or not qoj_name.strip():
            continue
        if qoj_name in result:
            raise RuntimeError(f"Duplicate QOJ name in {path}: {qoj_name}")
        result[qoj_name] = team["teamname"]
    if require_names and not result:
        raise RuntimeError(f"No QOJ team names found in {path}")
    return result


def qoj_name_map(path):
    return _qoj_name_map(load_teams(path), path)


def qoj_live_team_filter(official_path, unofficial_path):
    official_teams, unofficial_teams = load_live_teams(
        official_path, unofficial_path
    )
    result = _qoj_name_map(official_teams, official_path)
    unofficial_result = _qoj_name_map(
        unofficial_teams, unofficial_path, require_names=False
    )
    duplicate_names = sorted(set(result).intersection(unofficial_result))
    if duplicate_names:
        raise RuntimeError(
            "Duplicate QOJ names across official and unofficial teams: "
            + ", ".join(duplicate_names)
        )
    result.update(unofficial_result)
    return result, {team["teamname"] for team in unofficial_teams}


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


def _codeforces_team_id_map(teams, path, require_ids=True):
    result = {}
    for team in teams:
        team_ids = team.get("codeforces-team-id")
        if team_ids is None:
            continue
        if not isinstance(team_ids, list):
            team_ids = [team_ids]
        for raw_team_id in team_ids:
            team_id = int(raw_team_id)
            if team_id in result:
                raise RuntimeError(
                    f"Duplicate Codeforces team ID in {path}: {team_id}"
                )
            result[team_id] = team["teamname"]
    if require_ids and not result:
        raise RuntimeError(f"No Codeforces team IDs found in {path}")
    return result


def codeforces_team_id_map(path):
    return _codeforces_team_id_map(load_teams(path), path)


def codeforces_live_team_filter(official_path, unofficial_path):
    official_teams, unofficial_teams = load_live_teams(
        official_path, unofficial_path
    )
    result = _codeforces_team_id_map(official_teams, official_path)
    unofficial_result = _codeforces_team_id_map(
        unofficial_teams, unofficial_path, require_ids=False
    )
    duplicate_ids = sorted(set(result).intersection(unofficial_result))
    if duplicate_ids:
        raise RuntimeError(
            "Duplicate Codeforces team IDs across official and unofficial teams: "
            + ", ".join(map(str, duplicate_ids))
        )
    result.update(unofficial_result)
    return result, {team["teamname"] for team in unofficial_teams}


def codeforces_username_map(path):
    result = {}
    username_owners = {}
    for team in load_teams(path):
        raw_usernames = team.get("codeforces-usernames")
        if raw_usernames is None:
            continue
        if not isinstance(raw_usernames, list):
            raise RuntimeError(
                f"Invalid Codeforces usernames for team {team['teamname']!r}: "
                "expected an array"
            )

        usernames = []
        seen_usernames = set()
        for raw_username in raw_usernames:
            if not isinstance(raw_username, str) or not raw_username.strip():
                raise RuntimeError(
                    f"Invalid Codeforces username for team {team['teamname']!r}"
                )
            username = raw_username.strip()
            normalized = username.casefold()
            if normalized in seen_usernames:
                raise RuntimeError(
                    f"Duplicate Codeforces username {username!r} for team "
                    f"{team['teamname']!r}"
                )
            if normalized in username_owners:
                raise RuntimeError(
                    f"Codeforces username {username!r} belongs to both "
                    f"{username_owners[normalized]!r} and {team['teamname']!r}"
                )
            seen_usernames.add(normalized)
            username_owners[normalized] = team["teamname"]
            usernames.append(username)

        if usernames:
            result[team["teamname"]] = usernames

    if not result:
        raise RuntimeError(f"No Codeforces usernames found in {path}")
    return result
