import pandas
import sklearn
from sklearn.ensemble import RandomForestRegressor
import settings

def except_len(s):
    try:
        return len(s)
    except Exception:
        return 0

def mean(s):
    if len(s) > 0:
        return sum(s)/float(len(s))
    return 0

class RecordModel(object):
    def __init__(self):
        self.csv_data = pandas.read_csv(settings.FILE_PATH, index_col=False)

    def create_train_data(self):
        self.prev_predictors = ["wins", "points_for", "points_against", "points_diff", "off_points", "off_yards", "def_points", "def_yards", "takeaway_giveaway_ratio", "margin_of_victory", "strength_of_schedule", "simple_rating_system", "offensive_srs", "defensive_srs", "point_differential_rank", "yard_differential_rank"]
        csv_data = self.csv_data
        wins_dict = {}
        id_mapping = {}
        reverse_id_numbers = {}
        id_numbers = {}
        team_mapping = {}
        reverse_team_mapping = {}
        for team in settings.teams:
            team_wins = {}
            team_data = csv_data[csv_data["team"] == team]
            for id, row in team_data.iterrows():
                if row["year"] <= settings.MAX_YEAR:
                    team_wins[row["year"] + 1] = {k:row[k] for k in self.prev_predictors}
                    team_wins[row["year"] + 1]["point_differential_rank"] = row["point_differential_rank"] / row["teams_in_league"]
                    team_wins[row["year"] + 1]["yard_differential_rank"] = row["yard_differential_rank"] / row["teams_in_league"]
            wins_dict[team] = team_wins
        for id, row in csv_data.iterrows():
            id_mapping[row["gm_id"]] = row["gm_name"]
            id_mapping[row["owner_id"]] = row["owner_name"]
            id_mapping[row["coach_id"]] = row["coach_name"]

        sel_frame = csv_data[["team", "year", "coach_id", "gm_id", "owner_id", "wins", "gm_title", "owner_title"]]
        sel_frame = sel_frame[(sel_frame["year"] > 1960) & (sel_frame["year"] < 2014)]
        prev = {}
        for id, row in sel_frame.iterrows():
            info = wins_dict[row["team"]].get(row["year"], {})
            for k in self.prev_predictors:
                val = info.get(k, 0)
                if k not in prev:
                    prev[k] = []
                prev[k].append(val)

        for k in self.prev_predictors:
            n = "prev_{0}".format(k)
            sel_frame[n] = prev[k]

        for i, item in enumerate(id_mapping.keys()):
            id_numbers[i] = id_mapping[item]
            reverse_id_numbers[item] = i

        for i, team in enumerate(settings.teams.keys()):
            team_mapping[i] = team
            reverse_team_mapping[team] = i

        coach_num = []
        gm_num = []
        owner_num = []
        team_num = []
        for id, row in sel_frame.iterrows():
            owner_num.append(reverse_id_numbers[row["owner_id"]])
            gm_num.append(reverse_id_numbers[row["gm_id"]])
            coach_num.append(reverse_id_numbers[row["coach_id"]])
            team_num.append(reverse_team_mapping[row["team"]])

        sel_frame["coach_num"] = coach_num
        sel_frame["gm_num"] = gm_num
        sel_frame["owner_num"] = owner_num
        sel_frame["team_num"] = team_num

        rows = []
        for id, row in sel_frame.iterrows():
            preds = self.generate_row_predictors(row, sel_frame)
            rows.append(preds)
        sel_frame = pandas.concat(rows, axis=0)

        self.train_data = sel_frame
        self.id_mapping = id_mapping
        self.id_numbers = id_numbers
        self.reverse_id_numbers = reverse_id_numbers
        self.reverse_team_mapping = reverse_team_mapping
        self.team_mapping = team_mapping

    def generate_row_predictors(self, row, sel_frame):
        team_frame = sel_frame[(sel_frame["year"] < row["year"]) & (sel_frame["team"] == row["team"])]
        reg_frame = team_frame[(team_frame["coach_num"] == row["coach_num"]) & (team_frame["gm_num"] == row["gm_num"]) & (team_frame["owner_num"] == row["owner_num"])]
        regime_stability = len(reg_frame)

        coach_frame = team_frame[(team_frame["coach_num"] == row["coach_num"])]
        coach_stability = len(coach_frame)

        owner_frame = team_frame[(team_frame["owner_num"] == row["owner_num"])]
        owner_stability = len(owner_frame)

        gm_frame = team_frame[(team_frame["gm_num"] == row["gm_num"])]
        gm_stability = len(gm_frame)
        coach_wins_total = sum(coach_frame["wins"])
        coach_wins_avg = mean(coach_frame["wins"])
        owner_wins_total = sum(owner_frame["wins"])
        owner_wins_avg = mean(owner_frame["wins"])
        gm_wins_total = sum(gm_frame["wins"])
        gm_wins_avg = mean(gm_frame["wins"])
        regime_wins_total = sum(reg_frame["wins"])
        regime_wins_avg = mean(reg_frame["wins"])
        coach_yrs = len(sel_frame[(sel_frame["coach_num"] == row["coach_num"])])
        gm_yrs = len(sel_frame[(sel_frame["gm_num"] == row["gm_num"])])
        owner_yrs = len(sel_frame[(sel_frame["owner_num"] == row["owner_num"])])

        coach_teams = len(set(sel_frame[(sel_frame["coach_num"] == row["coach_num"])]["team"]))
        gm_teams = len(set(sel_frame[(sel_frame["coach_num"] == row["coach_num"])]["team"]))
        owner_teams = len(set(sel_frame[(sel_frame["coach_num"] == row["coach_num"])]["team"]))
        gm_title_len = len(row["gm_title"])
        owner_title_len = len(row["owner_title"])

        preds = pandas.DataFrame([regime_stability, coach_stability, owner_stability, gm_stability, coach_wins_total, coach_wins_avg, owner_wins_total,
                                  owner_wins_avg, gm_wins_total, gm_wins_avg, regime_wins_total, regime_wins_avg, coach_yrs, gm_yrs,
                                  owner_yrs, coach_teams, gm_teams, owner_teams, gm_title_len, owner_title_len])
        preds = preds.T
        preds.columns = ["regime_stability", "coach_stability", "gm_stability", "owner_stability", "coach_wins_total","coach_wins_avg","gm_wins_total","gm_wins_avg","owner_wins_total","owner_wins_avg","regime_wins_total","regime_wins_avg","coach_yrs","gm_yrs","owner_yrs","coach_teams","gm_teams","owner_teams", "gm_title_len", "owner_title_len"]
        preds = preds.T
        full_row = pandas.concat([row, preds], axis=0)
        return full_row.T

    def cross_validate(self):
        train_data = self.train_data
        clf = RandomForestRegressor(n_estimators=200, min_samples_leaf=10, random_state=1)
        kf = sklearn.cross_validation.KFold(len(train_data["wins"]), 3)
        real = []
        preds = []
        self.good_predictors = ["team_num", "coach_num", "gm_num", "owner_num", "prev_wins", "regime_stability", "coach_stability", "gm_stability", "owner_stability", "gm_title_len", "owner_title_len", "coach_wins_total","coach_wins_avg","gm_wins_total","gm_wins_avg","owner_wins_total","owner_wins_avg","regime_wins_total","regime_wins_avg","coach_yrs","gm_yrs","owner_yrs","coach_teams","gm_teams","owner_teams"]
        for k in self.prev_predictors:
            self.good_predictors.append("prev_{0}".format(k))
        for train, test in kf:
            clf.fit(train_data[self.good_predictors].iloc[train, :], train_data["wins"].iloc[train])
            actual = train_data["wins"].iloc[test]
            pred = pandas.DataFrame(clf.predict(train_data[self.good_predictors].iloc[test, :]))
            real.append(actual)
            preds.append(pred)
        all_real = pandas.concat(real, axis=0).reset_index()
        all_preds = pandas.concat(preds, axis=0).reset_index()
        pred_frame = pandas.concat([all_real, all_preds], axis=1)
        print ((sum((pred_frame.iloc[:,3] - pred_frame.iloc[:,1]) ** 2))/ len(pred_frame)) ** .5

        clf.fit(train_data[self.good_predictors], train_data["wins"])
        self.clf = clf

    def predict(self, team, updates):
        train_data = self.train_data
        team_info = train_data[(train_data["year"] == 2013) & (train_data["team"] == team)].iloc[0,:]
        x = team_info.index[0]
        reverse_id_mapping = {self.id_mapping[k]:k for k in self.id_mapping}
        for item in updates:
            val = updates[item]
            vid = reverse_id_mapping[val]
            num = self.reverse_id_numbers[vid]

            team_info["{0}_num".format(item)] = num
        new_row = self.generate_row_predictors(team_info, train_data)
        pred = self.clf.predict(team_info[self.good_predictors])
        print pred

    def get_positions(self):
        coaches = set(self.train_data["coach_name"])
        gms = set(self.train_data["gm_name"])
        owners = set(self.train_data["owners_name"])
        return {
            "coaches": coaches,
            "gms": gms,
            "owners": owners
        }

    def get_current_positions(self):
        team_pos = {}
        for t in settings.teams:
            team_info = self.csv_data[(self.csv_data["year"] == 2014) & (self.csv_data["team"] == t)].iloc[0,:]
            team_pos[t] = {
                "coach": team_info["coach_name"],
                "gm": team_info["gm_name"],
                "owner": team_info["owner_name"]
            }
        return team_pos

r = RecordModel()
r.create_train_data()
print r.cross_validate()
r.predict("nyg", {"coach": ""})



