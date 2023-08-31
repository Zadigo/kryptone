# import asyncio
# import json
# import time

# from selenium.webdriver import Edge
# from webdriver_manager.microsoft import EdgeChromiumDriverManager

# driver = Edge(EdgeChromiumDriverManager().install())


# async def main(url):
#     driver.get(url)
#     time.sleep(10)
#     result = driver.execute_async_script("""
#     var callback = arguments[arguments.length - 1]
#     window.setTimeout(() => {
#         async function resolveComment(item) {
#             const promise = new Promise((resolve, reject) => {
#                 // Javascript code used to parse the comments on
#                 // on a Google Maps business page
#                 let dataReviewId = item.dataset['reviewId']
#                 try {
#                     let moreButton = null

#                     moreButton = (
#                         // Try by getting the button using the specific review ID
#                         item.querySelector(`button[data-review-id="${dataReviewId}"][aria-controls="${dataReviewId}"][aria-expanded="false"]`) ||
#                         // Try the "Voir plus" button"
#                         item.querySelector('button[aria-label="Voir plus"]') ||
#                         // Try the "See more" button"
#                         item.querySelector('button[aria-label="See more"]') ||
#                         // On last resort try "aria-expanded"
#                         item.querySelector('button[aria-expanded="false"]')
#                     )
#                     moreButton.click()
#                 } catch (e) {
#                     console.info('No additional content for', dataReviewId)
#                 }

#                 setTimeout(() => {
#                     try {
#                         // Or, item.querySelector('.DU9Pgb').innerText
#                         period = item.querySelector('.rsqaWe').innerText
#                     } catch (e) {
#                         // pass
#                     }

#                     try {
#                         text = item.querySelector('.MyEned').innerText
#                     } catch (e) {
#                         text = ''
#                     }

#                     try {
#                         rating = item.querySelector('span[role="img"]').ariaLabel
#                     } catch (e) {
#                         // pass
#                     }

#                     resolve({
#                         id: dataReviewId,
#                         period: period,
#                         rating: rating,
#                         text: text
#                     })
#                 }, 1000)
#             })

#             // let comment = {}
#             const thenedPromise = promise.then((data) => {
#                 // comment = data
#                 return data
#             })

#             return await thenedPromise
#             // return comment
#         }

#         const result = Array.from(document.querySelectorAll('div[data-review-id^="Ch"]'))
#             .map(resolveComment)
#             .filter((item) => { return item !== undefined })

#         // Remove duplicate comments and null items
#         async function getComments() {
#             let c
#             c = await Promise.all(result)

#             function onlyUnique(value, index, array) {
#                 return array.indexOf(value) === index;
#             }

#             const seen = []
#             const cleanedComments = c.map((item) => {
#                 if (seen.includes(item.id)) {
#                     // pass
#                 } else {
#                     seen.push(item.id)
#                     return {
#                         id: item.id,
#                         period: item.period,
#                         rating: item.rating,
#                         text: item.text
#                     }
#                 }
#             }).filter(item => item !== undefined)

#             return cleanedComments
#         }

#         callback(getComments())
#     }, 8000)
#     """)
#     print(json.dumps(result))
#     time.sleep(5)
#     driver.quit()

# # if __name__ == '__main__':
# #     url = "https://www.google.com/maps/place/Bouddha+Wok/@50.6476347,3.1369403,14z/data=!4m8!3m7!1s0x47c329ea06cfabf9:0xb29eca5dde00934d!8m2!3d50.6518006!4d3.1253004!9m1!1b1!16s%2Fg%2F113h5ky3s?entry=ttu"
# #     asyncio.run(main(url))
