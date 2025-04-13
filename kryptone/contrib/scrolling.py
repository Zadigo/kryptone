class ScrollMixin:
    """A mixin that implements special scrolling
    functionnalities to the spider"""

    def scroll_window(self, wait_time=5, increment=1000, stop_at=None):
        """Scrolls the entire window by incremeting the current
        scroll position by a given number of pixels"""
        can_scroll = True
        new_scroll_pixels = 1000

        while can_scroll:
            scroll_script = f"""window.scroll(0, {new_scroll_pixels})"""

            self.driver.execute_script(scroll_script)
            # Scrolls until we get a result that determines that we
            # have actually scrolled to the bottom of the page
            has_reached_bottom = self.driver.execute_script(
                """return (window.innerHeight + window.scrollY) >= (document.documentElement.scrollHeight - 100)"""
            )
            if has_reached_bottom:
                can_scroll = False

            current_position = self.driver.execute_script(
                """return window.scrollY"""
            )
            if stop_at is not None and current_position > stop_at:
                can_scroll = False

            new_scroll_pixels = new_scroll_pixels + increment
            time.sleep(wait_time)

    def scroll_page_section(self, xpath=None, css_selector=None):
        """Scrolls a specific portion on the page"""
        if css_selector:
            selector = """const mainWrapper = document.querySelector('{condition}')"""
            selector = selector.format(condition=css_selector)
        else:
            # selector = self.evaluate_xpath(xpath)
            # selector = """const element = document.evaluate("{condition}", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null)"""
            # selector = selector.format(condition=xpath)
            pass

        body = """
        const elementToScroll = mainWrapper.querySelector('div[tabindex="-1"]')

        const elementHeight = elementToScroll.scrollHeight
        let currentPosition = elementToScroll.scrollTop

        // Indicates the scrolling speed
        const scrollStep = Math.ceil(elementHeight / {scroll_step})

        currentPosition += scrollStep
        elementToScroll.scroll(0, currentPosition)

        return [ currentPosition, elementHeight ]
        """.format(scroll_step=self.default_scroll_step)

        script = css_selector + '\n' + body
        return script

    def scroll_into_view(self, css_selector):
        """Scrolls directly into an element of the page"""
        script = """
        const el = document.querySelector('$css_selector')
        el.scrollIntoView({ behavior: 'smooth', block: 'end', inline: 'nearest' })
        """
        template = Template(script)
        script = template.substitute(**{'css_selector': css_selector})
        self.driver.execute_script(script)
