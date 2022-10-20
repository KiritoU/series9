import requests


from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from slugify import slugify
from time import sleep


from _db import database


from settings import CONFIG


class Helper:
    def get_header(self):
        header = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E150",  # noqa: E501
            "Accept-Encoding": "gzip, deflate",
            # "Cookie": CONFIG.COOKIE,
            "Cache-Control": "max-age=0",
            "Accept-Language": "vi-VN",
            "Referer": "https://mangabuddy.com/",
        }
        return header

    def error_log(self, msg: str, log_file: str = "failed.log"):
        datetime_msg = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(f"log/{log_file}", "a") as f:
            print(f"{datetime_msg} LOG:  {msg}\n{'-' * 80}", file=f)

    def download_url(self, url):
        return requests.get(url, headers=self.get_header())

    def format_text(self, text: str) -> str:
        return text.strip("\n").replace('"', "'").strip()

    def format_slug(self, slug: str) -> str:
        return slug.replace("’", "").replace("'", "")

    def add_https_to(self, url: str) -> str:
        if "http" not in url:
            url = "https:" + url

        return url

    def get_trailer_id(self, soup: BeautifulSoup) -> str:
        scripts = soup.find_all("script")
        for script in scripts:
            str_script = str(script)
            if "#pop-trailer" in str_script:
                splitted = str_script.split('"')
                for s in splitted:
                    if "https" in s:
                        return s.split("/")[-1]

        return ""

    def get_watching_href_and_fondo(self, soup: BeautifulSoup) -> list:
        try:
            main_detail = soup.find("div", class_="main-detail")
            main_category = main_detail.find("div", class_="main-category")

            watching_href = main_category.find("a", class_="mvi-cover").get("href")
            fondo_player = (
                main_category.find("a", class_="mvi-cover")
                .get("style")
                .replace("background-image: url(", "")
                .replace(");", "")
            )
            return [watching_href, fondo_player]

        except Exception as e:
            self.error_log(
                msg=f"Failed to find watching_href and fondo_player\n{str(soup)}\n{e}",
                log_file="watching_href.log",
            )
            return ["", ""]

    def get_title_and_season_number(self, series9_title: str) -> list:
        try:
            title = series9_title
            season_number = "1"

            for seasonSplitText in CONFIG.SEASON_SPLIT_TEXTS:
                if seasonSplitText in series9_title:
                    title, season_number = series9_title.split(seasonSplitText)
                    break

            return [self.format_text(title), self.format_text(season_number)]
        except Exception as e:
            self.error_log(
                msg=f"Failed to find title and season number\n{series9_title}\n{e}",
                log_file="helper.get_title_and_season_number.log",
            )

    def get_title_and_description(self, soup: BeautifulSoup) -> list:
        try:
            mvi_content = soup.find("div", class_="mvi-content")
            mvic_desc = mvi_content.find("div", class_="mvic-desc")

            title = mvic_desc.find("h3").text
            desc = mvic_desc.find("div", class_="desc").text

            return [self.format_text(title), self.format_text(desc)]

        except Exception as e:
            self.error_log(
                msg=f"Failed to find title and description\n{str(soup)}\n{e}",
                log_file="title_desc.log",
            )
            return ["", ""]

    def get_poster_url(self, soup: BeautifulSoup) -> str:
        try:
            mvi_content = soup.find("div", class_="mvi-content")
            mvic_thumb = mvi_content.find("div", class_="mvic-thumb")
            poster_url = (
                mvic_thumb.get("style")
                .replace("background-image: url(", "")
                .replace(");", "")
            )
            return poster_url

        except Exception as e:
            self.error_log(
                msg=f"Failed to get poster URL\n{str(soup)}\n{e}",
                log_file="poster_url.log",
            )
            return ""

    def get_left_data(self, mvici: BeautifulSoup) -> dict:
        res = {}
        for p in mvici.find_all("p"):
            key = p.find("strong").text.replace(":", "").strip()

            value = []
            a_elements = p.find_all("a")
            if (key == "Actor") and (len(a_elements) > 2):
                a_elements = a_elements[:-2]
            for a in a_elements:
                a_title = a.get("title")
                value.append(self.format_text(a_title))

            res[key] = value

        return res

    def get_right_data(self, mvici: BeautifulSoup) -> dict:
        res = {}
        for p in mvici.find_all("p"):
            strong_text = p.find("strong").text
            key = strong_text.replace(":", "").strip()
            value = p.text.replace(strong_text, "").strip()

            res[key] = value

        if "Duration" in res.keys():
            res["Duration"] = res["Duration"].replace("min", "").strip()
        return res

    def get_extra_info(self, soup: BeautifulSoup) -> dict:
        try:
            mvi_content = soup.find("div", class_="mvi-content")
            mvic_desc = mvi_content.find("div", class_="mvic-desc")
            mvic_info = mvic_desc.find("div", class_="mvic-info")
            mvici_left = mvic_info.find("div", class_="mvici-left")
            mvici_left_data = self.get_left_data(mvici_left)

            mvici_right = mvic_info.find("div", class_="mvici-right")
            mvici_right_data = self.get_right_data(mvici_right)

            mvici_data = {**mvici_left_data, **mvici_right_data}
            return mvici_data

        except Exception as e:
            self.error_log(
                msg=f"Failed to get extra info\n{str(soup)}\n{e}",
                log_file="extra_info.log",
            )

    def generate_post_data(
        self,
        title,
        description,
        post_type,
        trailer_id,
        fondo_player,
        poster_url,
        extra_info,
    ):
        post_data = {
            "description": description,
            "title": title,
            "post_type": post_type,
            # "id": "202302",
            "youtube_id": f"[{trailer_id}]",
            "serie_vote_average": extra_info["IMDb"],
            "episode_run_time": extra_info["Duration"],
            "fondo_player": fondo_player,
            "poster_url": poster_url,
            "category": extra_info["Genre"],
            "stars": extra_info["Actor"],
            "director": extra_info["Director"],
            "release-year": [extra_info["Release"]],
            "country": extra_info["Country"],
        }

        return post_data

    def get_players_iframes(self, links: list) -> list:
        players = []
        for link in links:
            players.append(CONFIG.IFRAME.format(link))

        return players

    def generate_episode_data(
        self,
        post_id,
        episode_name,
        season_number,
        episode_number,
        post_title,
        fondo_player,
        poster_url,
        quality,
        episode_links,
    ):
        players = self.get_players_iframes(episode_links)

        episode_data = {
            "post_id": post_id,
            "title": f"{post_title} Season {season_number} Episode {episode_number}",
            "description": "",
            "post_type": "episodes",
            # "ids": "202302",
            "season_number": season_number,
            "episode_number": episode_number,
            "serie": post_title,
            "name": episode_name,
            # "air_date": "2022-07-14",
            "fondo_player": fondo_player,
            "poster_serie": poster_url,
            "quality": quality,
            "players": players,
        }

        return episode_data

    def get_timeupdate(self) -> datetime:

        timeupdate = datetime.now() - timedelta(hours=7)

        return timeupdate

    def format_condition_str(self, equal_condition: str) -> str:
        return equal_condition.replace("\n", "").strip().lower()

    def insert_terms(self, post_id: int, terms: list, taxonomy: str):
        for term in terms:
            term_name = self.format_condition_str(term)
            cols = "tt.term_taxonomy_id"
            table = (
                f"{CONFIG.TABLE_PREFIX}term_taxonomy tt, {CONFIG.TABLE_PREFIX}terms t"
            )
            condition = f't.name = "{term_name}" AND tt.term_id=t.term_id AND tt.taxonomy="{taxonomy}"'

            be_term = database.select_all_from(
                table=table, condition=condition, cols=cols
            )
            if not be_term:
                term_id = database.insert_into(
                    table=f"{CONFIG.TABLE_PREFIX}terms",
                    data=(term, slugify(term), 0),
                )
                term_taxonomy_id = database.insert_into(
                    table=f"{CONFIG.TABLE_PREFIX}term_taxonomy",
                    data=(term_id, taxonomy, "", 0, 0),
                )
            else:
                term_taxonomy_id = be_term[0][0]

            try:
                database.insert_into(
                    table=f"{CONFIG.TABLE_PREFIX}term_relationships",
                    data=(post_id, term_taxonomy_id, 0),
                )
            except:
                pass

    def generate_post(self, post_data: dict) -> tuple:
        timeupdate = self.get_timeupdate()
        data = (
            0,
            timeupdate.strftime("%Y/%m/%d %H:%M:%S"),
            timeupdate.strftime("%Y/%m/%d %H:%M:%S"),
            post_data["description"],
            post_data["title"],
            "",
            "publish",
            "open",
            "closed",
            "",
            slugify(self.format_slug(post_data["title"])),
            "",
            "",
            timeupdate.strftime("%Y/%m/%d %H:%M:%S"),
            timeupdate.strftime("%Y/%m/%d %H:%M:%S"),
            "",
            0,
            "",
            0,
            post_data["post_type"],
            "",
            0,
        )
        return data

    def insert_post(self, post_data: dict) -> int:
        data = self.generate_post(post_data)
        post_id = database.insert_into(table=f"{CONFIG.TABLE_PREFIX}posts", data=data)
        return post_id

    def insert_film(self, post_data: dict) -> int:
        try:
            post_id = self.insert_post(post_data)
            timeupdate = self.get_timeupdate()

            postmeta_data = [
                (post_id, "_edit_last", "1"),
                (post_id, "_edit_lock", f"{int(timeupdate.timestamp())}:1"),
                (post_id, "time", ""),
                (post_id, "timezone", ""),
                # (post_id, "id", post_data["id"]),
                (post_id, "featureds_img", ""),
                (
                    post_id,
                    "poster_url",
                    post_data["poster_url"],
                ),
                (
                    post_id,
                    "fondo_player",
                    post_data["fondo_player"],
                ),
                (
                    post_id,
                    "imagenes",
                    "",
                ),
                (post_id, "youtube_id", post_data["youtube_id"]),
                (post_id, "original_name", post_data["title"]),
                (post_id, "first_air_date", ""),
                (post_id, "last_air_date", ""),
                (post_id, "notice_s", "0"),
                (post_id, "_notice_s", "field_5b4c2d7154b68"),
                (post_id, "ddw", "0"),
                (post_id, "_ddw", "field_54fa4e8cbca22"),
                (post_id, "voo", "0"),
                (post_id, "_voo", "field_54fa4f41bca28"),
                (post_id, "subt", "0"),
                (post_id, "_subt", "field_58b5255a24d0f"),
            ]

            tvseries_postmeta_data = [
                (post_id, "next-ep", ""),
                (post_id, "tv_eps_num", ""),
                (post_id, "serie_vote_average", post_data["serie_vote_average"]),
                (post_id, "episode_run_time", post_data["episode_run_time"]),
                (post_id, "temporadas", "0"),
                (post_id, "_temporadas", "field_58718d88c2bf9"),
            ]

            movie_postmeta_data = [
                (post_id, "imdbRating", post_data["serie_vote_average"]),
                (post_id, "Runtime", f"{post_data['episode_run_time']} min"),
            ]

            if post_data["post_type"] == "tvshows":
                postmeta_data.extend(tvseries_postmeta_data)
            else:
                postmeta_data.extend(movie_postmeta_data)

            for row in postmeta_data:
                database.insert_into(
                    table=f"{CONFIG.TABLE_PREFIX}postmeta",
                    data=row,
                )

            for taxonomy in CONFIG.TAXONOMIES:
                if taxonomy in post_data.keys() and post_data[taxonomy]:
                    self.insert_terms(
                        post_id=post_id, terms=post_data[taxonomy], taxonomy=taxonomy
                    )

            return post_id
        except Exception as e:
            self.error_log(f"Failed to insert film\n{e}")

    def update_meta_key(self, post_id, meta_key, update_value, field) -> list:
        condition = f'post_id={post_id} AND meta_key="{meta_key}"'
        post_temporadas_episodios = database.select_all_from(
            table="wp_postmeta", condition=condition
        )
        if post_temporadas_episodios:
            value = int(post_temporadas_episodios[0][-1])
            if value < update_value:
                database.update_table(
                    table=f"{CONFIG.TABLE_PREFIX}postmeta",
                    set_cond=f"meta_value={update_value}",
                    where_cond=condition,
                )
            return []
        else:
            return [
                (
                    post_id,
                    meta_key,
                    update_value,
                ),
                (post_id, f"_{meta_key}", field),
            ]

    def generate_players_postmeta_data(
        self, episode_id, players: list, quality: str
    ) -> list:
        res = []
        for i in range(len(players)):
            iframe = players[i]
            res.extend(
                [
                    (episode_id, f"player_{i}_name_player", ""),
                    (episode_id, f"_player_{i}_name_player", "field_5a6ae00d1df8f"),
                    (episode_id, f"player_{i}_type_player", "p_embed"),
                    (episode_id, f"_player_{i}_type_player", "field_591fd3cc1c291"),
                    (episode_id, f"player_{i}_quality_player", quality),
                    (episode_id, f"_player_{i}_quality_player", "field_5640cc8323220"),
                    (
                        episode_id,
                        f"player_{i}_embed_player",
                        iframe,
                    ),
                    (episode_id, f"_player_{i}_embed_player", "field_5640cc9823221"),
                ]
            )
        return res

    def insert_episode(self, episode_data: dict):
        season_number = int(episode_data["season_number"])
        episode_number = int(episode_data["episode_number"])

        episode_id = self.insert_post(episode_data)
        players = episode_data["players"]
        temporadas_episodios = (
            f"temporadas_{season_number-1}_episodios_{episode_number-1}"
        )

        postmeta_data = [
            # (episode_id, "ids", episode_data["ids"]),
            (episode_id, "temporada", season_number),
            (episode_id, "episodio", episode_number),
            (episode_id, "serie", episode_data["serie"]),
            (episode_id, "season_number", season_number),
            (episode_id, "episode_number", episode_number),
            (episode_id, "name", episode_data["name"]),
            # (episode_id, "air_date", episode_data["air_date"]),
            (episode_id, "fondo_player", episode_data["fondo_player"]),
            (episode_id, "poster_serie", episode_data["poster_serie"]),
            (episode_id, "player", str(len(players))),
            (episode_id, "_player", "field_5640ccb223222"),
            (episode_id, "_edit_last", "1"),
            (episode_id, "ep_pagination", "default"),
            (episode_id, "notice_s", "0"),
            (episode_id, "_notice_s", "field_5b4c2d7154b68"),
            (
                episode_data["post_id"],
                f"{temporadas_episodios}_slug",
                slugify(self.format_slug(episode_data["title"])),
            ),
            (
                episode_data["post_id"],
                f"_{temporadas_episodios}_slug",
                "field_58718dccc2bfb",
            ),
            (episode_data["post_id"], f"{temporadas_episodios}_titlee", ""),
            (
                episode_data["post_id"],
                f"_{temporadas_episodios}_titlee",
                "field_58718ddac2bfc",
            ),
        ]

        postmeta_data.extend(
            self.update_meta_key(
                post_id=episode_data["post_id"],
                meta_key="temporadas",
                update_value=season_number,
                field="field_58718d88c2bf9",
            )
        )

        postmeta_data.extend(
            self.update_meta_key(
                post_id=episode_data["post_id"],
                meta_key=f"temporadas_{season_number - 1}_episodios",
                update_value=episode_number,
                field="field_58718dabc2bfa",
            )
        )

        postmeta_data.extend(
            self.generate_players_postmeta_data(
                episode_id, players, episode_data["quality"]
            )
        )

        for row in postmeta_data:
            database.insert_into(
                table=f"{CONFIG.TABLE_PREFIX}postmeta",
                data=row,
            )
            sleep(0.1)

        sleep(0.1)


helper = Helper()

if __name__ == "__main__":
    print("Helper running...")
