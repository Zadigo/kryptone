function gatherComments() {
    const commentsWrapper = document.querySelectorAll("div[data-review-id^='Ch'][class*='fontBodyMedium ']")

    Array.from(commentsWrapper).forEach((item) => {
        let dataReviewId = item.dataset['reviewId']
        try {
            // Sometimes there is a read more button
            // that we have to click

            moreButton = (
                // Try the "Voir plus" button"
                item.querySelector('button[aria-label="Voir plus"]') ||
                // Try the "See more" button"
                item.querySelector('button[aria-label="See more"]') ||
                // On last resort try "aria-expanded"
                item.querySelector('button[aria-expanded="false"]')
            )
            moreButton.click()
        } catch (e) {
            console.log('No "see more" button for review', dataReviewId)
        }
    })

    return Array.from(commentsWrapper).map((item) => {
        let dataReviewId = item.dataset['reviewId']

        // Or, .rsqaWe
        let period = item.querySelector('.DU9Pgb') && item.querySelector('.DU9Pgb').textContent
        let rating = item.querySelector('span[role="img"]') && item.querySelector('span[role="img"]').ariaLabel
        let text = item.querySelector("*[class='MyEned']") && item.querySelector("*[class='MyEned']").textContent
        let reviewerName = item.querySelector('[class*="d4r55"]') && item.querySelector('[class*="d4r55"]').textContent
        let reviewerNumberOfReviews = item.querySelector('*[class*="RfnDt"]') && item.querySelector('*[class*="RfnDt"]').textContent

        return {
            review_id: dataReviewId,
            text,
            rating,
            period,
            reviewer: {
                name: reviewerName,
                number_of_reviews: reviewerNumberOfReviews
            }
        }
    })
}
return gatherComments()
