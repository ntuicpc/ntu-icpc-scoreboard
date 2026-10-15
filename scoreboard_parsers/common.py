def time_to_minutes(value):
    hours, minutes = map(int, value.split(":"))
    return hours * 60 + minutes


def mark_first_solves(teams, problems):
    first_solve_times = {problem: None for problem in problems}
    for team in teams:
        for problem in problems:
            result = team["problems"][problem]
            if result["status"] != "accepted" or result["time"] is None:
                continue
            solve_time = time_to_minutes(result["time"])
            current = first_solve_times[problem]
            if current is None or solve_time < current:
                first_solve_times[problem] = solve_time

    for team in teams:
        for problem in problems:
            result = team["problems"][problem]
            if result["status"] != "accepted" or result["time"] is None:
                continue
            if time_to_minutes(result["time"]) == first_solve_times[problem]:
                result["status"] = "first-solve"


def sort_and_assign_ranks(teams):
    teams.sort(key=lambda team: (-team["solved"], team["penalty"], team["rank"]))
    previous_result = None
    current_rank = 0
    for index, team in enumerate(teams, start=1):
        result = (team["solved"], team["penalty"])
        if result != previous_result:
            current_rank = index
            previous_result = result
        team["rank"] = current_rank


def keep_official_teams(scoreboard, official_teamnames):
    problems = scoreboard["problems"]
    teams = [
        team
        for team in scoreboard["teams"]
        if team.get("name") in official_teamnames
    ]

    for team in teams:
        team.pop("unofficial", None)
        for problem in problems:
            result = team["problems"][problem]
            if result.get("status") == "first-solve":
                result["status"] = "accepted"

    mark_first_solves(teams, problems)
    sort_and_assign_ranks(teams)
    scoreboard["teams"] = teams
    return scoreboard
