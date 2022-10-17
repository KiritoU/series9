import logging

from time import sleep

from _db import database
from settings import CONFIG

logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", level=logging.INFO)


def delete_with(post_type):
    post_ids = database.select_all_from(
        table=f"{CONFIG.TABLE_PREFIX}posts",
        condition=f'post_type="{post_type}"',
        cols="ID",
    )
    post_ids = [x[0] for x in post_ids]

    for post_id in post_ids:
        logging.info("Deleting post: {0}".format(post_id))

        database.delete_from(
            table=f"{CONFIG.TABLE_PREFIX}postmeta",
            condition=f'post_id="{post_id}"',
        )

        database.delete_from(
            table=f"{CONFIG.TABLE_PREFIX}term_relationships",
            condition=f'object_id="{post_id}"',
        )

        database.delete_from(
            table=f"{CONFIG.TABLE_PREFIX}posts",
            condition=f'ID="{post_id}"',
        )
        sleep(0.1)


def main():
    post_types = ["tvshows", "episodes", "post"]
    for post_type in post_types:
        delete_with(post_type)


def delete(postId):
    database.delete_from(table=f"{CONFIG.TABLE_PREFIX}posts", condition=f"ID={postId}")
    database.delete_from(
        table=f"{CONFIG.TABLE_PREFIX}postmeta", condition=f"post_id={postId}"
    )


if __name__ == "__main__":
    # delete(131)
    main()
