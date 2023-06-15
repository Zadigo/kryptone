import time

from kryptone.app import SinglePageAutomater


class EcommerceMixin:
    scroll_step = 30
    def scroll_page(self):
        can_scroll = True
        previous_scroll_position = None
        while can_scroll:
            script = f"""
            // Scrolls the whole page of a website
            const documentHeight = document.documentElement.offsetHeight
            let currentPosition = document.documentElement.scrollTop

            const scrollStep = Math.ceil(documentHeight / {self.scroll_step})
            currentPosition += scrollStep
            document.documentElement.scroll(0, currentPosition)
            return [documentHeight, currentPosition]
            """
            result = self.driver.execute_script(script)
            document_height, scroll_position = result
            if scroll_position is not None and scroll_position == previous_scroll_position:
                can_scroll = False
            previous_scroll_position = scroll_position
            time.sleep(2)


class Etam(EcommerceMixin, SinglePageAutomater):
    start_url = 'https://int.etam.com/en_CA/knickers/all-bottoms'

    def run_actions(self, current_url, **kwargs):
        self.scroll_page()


if __name__ == '__main__':
    try:
        instance = Etam()
        instance.start(wait_time=1)
    except KeyboardInterrupt:
        pass
    except Exception:
        pass
