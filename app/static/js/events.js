function getGenerateSceneUpdates(
    taskId,
    $generateSceneContent,
    $generateSceneError,
    $generateSceneLoader,
    $generateSceneButton,
) {

    function promoteGeneratedScene(newContent) {
        $generateSceneContent.text(newContent);
    }

    console.log('[getGenerateSceneUpdates] taskId=', taskId);

    const url = `ws://localhost:8004/ws/${taskId}`;

    socket = new ReconnectingWebSocket(url);

    socket.debug = true

    socket.onopen = ()=>{
        // $('#websocket-status').removeClass('reconnecting').addClass('open')
        console.log('websocket open')
        socket.send('connect')
    }

    socket.onclose = ()=>{
        // $('#websocket-status').removeClass('open').addClass('reconnecting')
        console.log('websocket closed')
    }

    let sceneGenerateBlock = false;
    let messageQueue = [];
    let sceneGenerateContent = '';

    var addTextByDelay = function(text, elem, delay, finishCallback) {
        if (text.length > 0) {
            // Append first character 
            elem.append(text[0]);
            setTimeout(function () {
                // Slice text by 1 character and call function again                
                addTextByDelay(text.slice(1), elem, delay, finishCallback);
            }, delay);
        } else {
            finishCallback && finishCallback();
        }
    }

    async function processNextMessage() {
        if (messageQueue.length > 0) {
            const data = messageQueue.shift();
            sceneGenerateBlock = true;
            let newContent = data.task_results.content;

            if (sceneGenerateContent.length) {
                let lengthDiff = sceneGenerateContent.length - newContent.length;
                newContent = data.task_results.content.slice(lengthDiff);
            }

            console.log('newContent is ', newContent);

            await new Promise(resolve => {
                addTextByDelay(newContent, $generateSceneContent, 1, () => {
                    sceneGenerateBlock = false;
                    resolve(); // Resolve the promise to continue processing the next message
                });
            });

            sceneGenerateContent = data.task_results.content;
            console.log('try finished');

            // Process the next message in the queue
            await processNextMessage();
        }
    }


    socket.onmessage = async (msg) => {
        let data = {};
        console.log('websocket message', msg);
        try {
            data = msg.data && JSON.parse(msg.data);
            console.log('sceneGenerateBlock', sceneGenerateBlock);
            if (data.task_results && data.type == 'scene_generate' && data.task_results.content) {
                messageQueue.push(data);
                if (!sceneGenerateBlock) {
                    await processNextMessage();
                }
                if (data.succeeded) {
                    console.log('SCENE GENERATION FINISHED');
                    $generateSceneLoader.hide();
                    $generateSceneButton.prop('disabled', false);
                    promoteGeneratedScene(sceneGenerateContent)
                }
            }
            
        } catch (err) {
            console.log('websocket is not JSON');
        }
    }

}