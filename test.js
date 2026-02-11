import { Client } from "@gradio/client";

async function checkApi() {
    const app = await Client.connect("Yuanshi/OminiControl");
    const api_info = await app.view_api();
    console.log(JSON.stringify(api_info, null, 2));
}
checkApi();