import subprocess
import sys
import os
import argparse
from logger import logger

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
PYTHON_EXEC = sys.executable


def build_steps(queries=None, subreddits=None):
    """Build step commands, optionally with query overrides."""
    steps = []

    amazon_cmd = [PYTHON_EXEC, "scrapers/amazon_mvp.py"]
    if queries:
        amazon_cmd.extend(["--queries", queries])
    steps.append(("Amazon Scraper", amazon_cmd))

    ebay_cmd = [PYTHON_EXEC, "scrapers/ebay_mvp.py"]
    if queries:
        ebay_cmd.extend(["--queries", queries])
    steps.append(("eBay Scraper", ebay_cmd))

    # Disabled Scrapers (SerpApi limitations or API access issues):
    # - Etsy: Needs commercial API access
    # - AliExpress: SerpApi returns no results






    # Reddit Scraper - Disabled for E-commerce Focus
    # reddit_cmd = [PYTHON_EXEC, "scrapers/reddit_mvp.py"]
    # if subreddits:
    #     reddit_cmd.extend(["--subreddits", subreddits])
    # steps.append(("Reddit Scraper", reddit_cmd))

    # YouTube Scraper - Disabled for E-commerce Focus
    # youtube_cmd = [PYTHON_EXEC, "scrapers/youtube_mvp.py"]
    # if queries:
    #     youtube_cmd.extend(["--queries", queries])
    # steps.append(("YouTube Scraper", youtube_cmd))

    # SERP Discovery step removed as per user request
    # serp_cmd = [PYTHON_EXEC, "scrapers/serp_discovery.py"]
    # ...


    steps.append(("Trend Intelligence Pipeline", [PYTHON_EXEC, "pipeline.py"]))
    return steps


def run_step(name, command):
    logger.info(f"Starting step: {name}")
    try:
        result = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            logger.error(
                f"Step failed: {name} | stderr: {result.stderr}"
            )
        else:
            logger.info(f"Step completed successfully: {name}")

    except Exception as e:
        logger.error(f"Execution error in step {name} | {e}")


def main():
    parser = argparse.ArgumentParser(description="Run full trend pipeline")
    parser.add_argument(
        "--queries",
        type=str,
        default=None,
        help='Comma-separated search queries for Amazon & YouTube, e.g. "headphones,air fryer,gaming laptop"',
    )
    parser.add_argument(
        "--subreddits",
        type=str,
        default=None,
        help='Reddit subreddits as "vertical:sub1,sub2;vertical2:sub3"',
    )
    args = parser.parse_args()

    steps = build_steps(queries=args.queries, subreddits=args.subreddits)
    logger.info("Pipeline execution started")

    for step_name, cmd in steps:
        run_step(step_name, cmd)

    logger.info("Pipeline execution completed")
    print("Pipeline run completed successfully. Check pipeline.log for details.")


if __name__ == "__main__":
    main()
