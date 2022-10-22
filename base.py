import logging

from bs4 import BeautifulSoup
from time import sleep


from settings import CONFIG
from helper import helper
from _db import database

logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", level=logging.INFO)


class Crawler_Site:
    def crawl_soup(self, url):
        logging.info(f"Crawling {url}")

        html = helper.download_url(url)
        soup = BeautifulSoup(html.content, "html.parser")

        return soup

    def get_episodes_data(self, watching_href: str) -> dict:
        if "http" not in watching_href:
            watching_href = CONFIG.SERIES9_HOMEPAGE + watching_href

        res = {}
        try:
            soup = self.crawl_soup(watching_href)

            main_detail = soup.find("div", class_="main-detail")
            mv_info = main_detail.find("div", {"id": "mv-info"})
            list_eps = mv_info.find("div", {"id": "list-eps"})
            servers = list_eps.find_all("div", class_="le-server")
            for server in servers:
                les_content = server.find("div", class_="les-content")
                episodes = les_content.find_all("a")
                for episode in episodes:
                    title = episode.get("title")
                    player_data = episode.get("player-data")
                    episode_data = episode.get("episode-data")

                    res.setdefault(episode_data, {})
                    res[episode_data].setdefault("title", "")
                    res[episode_data].setdefault("links", [])

                    if res[episode_data]["title"] != title:
                        res[episode_data]["title"] = title
                    res[episode_data]["links"].append(player_data)

        except Exception as e:
            helper.error_log(
                f"Failed to get episode information\n{watching_href}\n{e}",
                log_file="episodes.log",
            )

        return res

    def crawl_episodes(
        self,
        post_id,
        post_type,
        watching_href,
        post_title,
        season_number,
        fondo_player,
        poster_url,
        quality,
    ):
        episodes_data = self.get_episodes_data(watching_href)

        lenEpisodes = len(episodes_data.keys())
        for episode_number, episode in episodes_data.items():
            # for i in range(lenEpisodes):
            if (post_type == "tvshows") or (lenEpisodes > 1):
                if post_type == "post":
                    if (episode_number == "0") or (episode_number == 0):
                        episode_number = "1"

                    database.update_table(
                        table=f"{CONFIG.TABLE_PREFIX}posts",
                        set_cond=f'post_type="tvshows"',
                        where_cond=f"ID={post_id}",
                    )

                    database.update_table(
                        table=f"{CONFIG.TABLE_PREFIX}postmeta",
                        set_cond=f'meta_key="serie_vote_average"',
                        where_cond=f'post_id={post_id} AND meta_key="imdbRating"',
                    )

                    database.update_table(
                        table=f"{CONFIG.TABLE_PREFIX}postmeta",
                        set_cond=f'meta_key="episode_run_time"',
                        where_cond=f'post_id={post_id} AND meta_key="Runtime"',
                    )

                    tvseries_postmeta_data = [
                        (post_id, "next-ep", ""),
                        (post_id, "tv_eps_num", ""),
                        (post_id, "temporadas", "0"),
                        (post_id, "_temporadas", "field_58718d88c2bf9"),
                    ]

                    for row in tvseries_postmeta_data:
                        database.insert_into(
                            table=f"{CONFIG.TABLE_PREFIX}postmeta",
                            data=row,
                        )

                episode_title = (
                    f"{post_title} Season {season_number} Episode {episode_number}"
                )

                condition = f'post_title = "{episode_title}"'
                be_post = database.select_all_from(
                    table=f"{CONFIG.TABLE_PREFIX}posts", condition=condition
                )
                if be_post:
                    continue

                episode_data = helper.generate_episode_data(
                    post_id,
                    episode["title"],
                    season_number,
                    episode_number,
                    post_title,
                    fondo_player,
                    poster_url,
                    quality,
                    episode["links"],
                )

                helper.insert_episode(episode_data)
            else:
                players = helper.get_players_iframes(episode["links"])
                postmeta_data = [
                    (post_id, "player", str(len(players))),
                    (post_id, "_player", "field_5640ccb223222"),
                ]
                postmeta_data.extend(
                    helper.generate_players_postmeta_data(post_id, players, quality)
                )

                for row in postmeta_data:
                    database.insert_into(
                        table=f"{CONFIG.TABLE_PREFIX}postmeta",
                        data=row,
                    )
                    sleep(0.1)

    def crawl_film(self, href: str, post_type: str = "tvshows"):
        soup = self.crawl_soup(href)

        title, description = helper.get_title_and_description(soup)
        watching_href, fondo_player = helper.get_watching_href_and_fondo(soup)
        if not watching_href:
            watching_href += "/watching.html"

        poster_url = helper.get_poster_url(soup)

        fondo_player = helper.add_https_to(fondo_player)
        poster_url = helper.add_https_to(poster_url)

        trailer_id = helper.get_trailer_id(soup)
        extra_info = helper.get_extra_info(soup)

        if not title:
            helper.error_log(msg=f"No title was found\n{href}", log_file="no_title.log")
            return

        if post_type == "tvshows":
            post_title, season_number = helper.get_title_and_season_number(title)
        else:
            post_title = title
            season_number = "1"

        condition = f'post_title = "{post_title}" AND post_type="{post_type}"'
        be_post = database.select_all_from(
            table=f"{CONFIG.TABLE_PREFIX}posts", condition=condition
        )
        if not be_post:

            post_data = helper.generate_post_data(
                post_title,
                description,
                post_type,
                trailer_id,
                fondo_player,
                poster_url,
                extra_info,
            )

            post_id = helper.insert_film(post_data)
        else:
            post_id = be_post[0][0]

        self.crawl_episodes(
            post_id,
            post_type,
            watching_href,
            post_title,
            season_number,
            fondo_player,
            poster_url,
            extra_info["Quality"],
        )

    def crawl_page(self, url, post_type: str = "tvshows"):

        soup = self.crawl_soup(url)

        movies_list = soup.find("div", class_="movies-list")
        if not movies_list:
            return

        ml_items = movies_list.find_all("div", class_="ml-item")
        if not ml_items:
            return

        for item in ml_items:
            try:
                href = item.find("a").get("href")

                if "http" not in href:
                    href = CONFIG.SERIES9_HOMEPAGE + href

                self.crawl_film(href=href, post_type=post_type)

            except Exception as e:
                helper.error_log(f"Failed to get href\n{item}\n{e}", "page.log")


if __name__ == "__main__":
    # Crawler_Site().crawl_page(CONFIG.SERIES9_MOVIES_LATEST_PAGE)
    # Crawler_Site().crawl_episodes(
    #     1, "https://series9.la/film/country-queen-season-1/watching.html", "", "", ""
    # )

    Crawler_Site().crawl_film("https://series9.la//film/crossing-lines-season-1-vwd")
    Crawler_Site().crawl_film("https://series9.la//film/crossing-lines-season-2-cdw")
    Crawler_Site().crawl_film("https://series9.la//film/crossing-lines-season-3-wds")

    # Crawler_Site().crawl_film(
    #     "https://series9.la//film/ghost-adventures-bwm", post_type="post"
    # )

    # Crawler_Site().crawl_film("https://series9.la//film/ghost-adventures-season-1-utc")
