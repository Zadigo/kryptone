(async () => {
    var promise1 = new Promise(function (resolve, reject) {
        resolve('foo')
    })

    let myval = ""
    var thenedPromise = promise1.then(function (value) {
        myval = value
        console.log(value)
    })

    await thenedPromise

    console.log(myval)
})()

