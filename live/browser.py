def download_html(platform, url, ready_selector=None, ready_timeout=90):
    from selenium import webdriver
    from selenium.common.exceptions import TimeoutException
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait

    options = webdriver.ChromeOptions()
    options.page_load_strategy = "normal"
    print(f"[{platform}] Starting Chrome...", flush=True)
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(30)
    try:
        try:
            print(f"[{platform}] Loading scoreboard: {url}", flush=True)
            driver.get(url)
            print(f"[{platform}] Scoreboard page loaded successfully.", flush=True)
        except TimeoutException:
            print(
                f"[{platform}] Page load timed out after 30 seconds; "
                "continuing with the HTML currently available.",
                flush=True,
            )

        ready_state = driver.execute_script("return document.readyState")
        print(f"[{platform}] Browser document.readyState: {ready_state}", flush=True)
        if ready_selector:
            print(
                f"[{platform}] Waiting for the standings table "
                f"(up to {ready_timeout} seconds)...",
                flush=True,
            )
            try:
                WebDriverWait(driver, ready_timeout).until(
                    lambda current: current.find_elements(By.CSS_SELECTOR, ready_selector)
                )
            except TimeoutException as error:
                title = driver.title or "(no title)"
                raise RuntimeError(
                    f"{platform} standings did not appear after {ready_timeout} seconds; "
                    f"current page title: {title!r}."
                ) from error
            print(f"[{platform}] Standings table is ready.", flush=True)
        html = driver.page_source
    finally:
        driver.quit()

    print(
        f"[{platform}] Captured {len(html):,} characters of HTML and closed Chrome.",
        flush=True,
    )
    return html
