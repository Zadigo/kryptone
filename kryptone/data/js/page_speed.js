var navigationEntries = null
var timingData = {}

function calculateSpeed() {
    if (performance && performance.getEntriesByType) {
        navigationEntries = performance.getEntriesByType('navigation')
        if (navigationEntries.length > 0) {
            var entry = navigationEntries[0]
            timingData = {
                page_load_time: entry.fetchStart - entry.loadEventStart,
                page_download_time: entry.responseEnd - entry.responseStart,
                dns_time: entry.domainLookupEnd - entry.domainLookupStart,
                server_response_time: entry.responseStart - entry.requestStart,
                tcp_connect_time: entry.connectEnd - entry.connectStart,
                dom_interactive_time: entry.domInteractive - entry.fetchStart,
                content_load_time: entry.domContentLoadedEventStart - entry.fetchStart,
                page_completed: entry.loadEventEnd - entry.fetchStart
                // 'redirect_response_time': pt.fetchStart - pt.navigationStart,
            }
        }
    }
    return timingData
}

return calculateSpeed()
