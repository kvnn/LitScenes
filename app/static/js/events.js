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

var addTextByDelay = function (text, elem, delay, finishCallback) {
    let currentIndex = 0;
    
    const animate = () => {
        if (currentIndex < text.length) {
            elem.append(text[currentIndex]);
            currentIndex++;
            requestAnimationFrame(animate);
        } else {
            finishCallback && finishCallback();
        }
    };
    
    animate();
};


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

        await new Promise(resolve => {
            addTextByDelay(newContent, $('#generate_scene_content'), 1, () => {
                sceneGenerateBlock = false;
                resolve(); // Resolve the promise to continue processing the next message
            });
        });

        scene_generate_tasks[data.task_id].content = data.task_results.content;
        console.log('try finished');

        // Process the next message in the queue
        await processNextMessage();
    }
}

window.socket = socket;

