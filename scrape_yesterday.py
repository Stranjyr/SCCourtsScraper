import webscraper
from datetime import datetime, timedelta

def scrape_yesterday():
    yesterday = datetime.now() - timedelta(days=1)
    courts = ["Blythewood Magistrate",
              "Colombia Magistrate",
              "Colombia Municipal Court",
              "Dentsville Magistrate",
              "Dutch Fork Magistrate",
              "Eastover Magistrate",
              "Hopkins Magistrate",
              "Lykesland Magistrate",
              "Olympia Magistrate",
              "Pontiac Magistrate",
              "Richland County General Sessions",
              "Upper Township Magistrate",
              "Waverly Magistrate"]

    agent = webscraper.DatabaseAgent("central_index_dev", "central_index_daily_log", 10)
    agent.daterange_thread_controller(timedelta(days=1),
                                      yesterday,
                                      yesterday + timedelta(days=1),
                                      courts,
                                      headless=True)


if __name__ == "__main__":
    scrape_yesterday()