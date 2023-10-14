const url = "ws://localhost:8004/ws";

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

scene_generate_tasks = {

}

async function addTextByDelay(text, elem, charactersPerInterval, delay, finishCallback) {
    let currentIndex = 0;

    async function appendCharactersBatch() {
        for (let i = 0; i < charactersPerInterval && currentIndex < text.length; i++) {
            elem.append(text[currentIndex]);
            currentIndex++;
        }

        if (currentIndex < text.length) {
            await new Promise(resolve => setTimeout(resolve, delay));
            await appendCharactersBatch();
        } else {
            finishCallback && finishCallback();
        }
    }

    await appendCharactersBatch();
}


let sceneGenerateBlock = false;
let messageQueue = [];

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
        }
    } catch (err) {
        console.log('websocket is not JSON');
    }
}

async function processNextMessage() {
    if (messageQueue.length > 0) {
        const data = messageQueue.shift();
        sceneGenerateBlock = true;
        scene_generate_tasks[data.task_id] = scene_generate_tasks[data.task_id] || {};
        scene_generate_tasks[data.task_id].content = scene_generate_tasks[data.task_id].content || '';
        let lengthDiff = data.task_results.content.length - scene_generate_tasks[data.task_id].content.length;
        let newContent = data.task_results.content.slice(lengthDiff);
        console.log('newContent is ', newContent);

        addTextByDelay(newContent, $('#generate_scene_content'), 1, 10, () => {
            sceneGenerateBlock = false;
        });

        scene_generate_tasks[data.task_id].content = data.task_results.content;
        console.log('try finished');

        // Process the next message in the queue
        await processNextMessage();
    }
}

window.socket = socket;

