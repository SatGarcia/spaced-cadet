

/** Updates the hidden response field in a Fill In The Blank Question form
 *  based on user input.*/
function Update_FITB_Response_Field() {
    let textbox_num = 1;
    let response_list = [];
        
    //adding all the textboxes to the repsonse list until they dont exist by ID
    while (document.getElementById(`FITB${textbox_num}`) != null){
        //The exact thing that the user put into the text box
        let originalResponse = document.getElementById(`FITB${textbox_num}`).value;
        let response_msg = JSON.stringify(document.getElementById(`FITB${textbox_num}`).value);
        response_list.push(response_msg);
        textbox_num ++;
    }
	
	// Build the response string based on the order of the items in the
	// list.
	let response_str = "";

	// loop through every textbox in the question
    for (let item of response_list) {
		response_str = response_str + item+",";
	}

    //removing the extra comma at the end
    let lastComma = response_str.length -1;
    response_str = response_str.slice(0, lastComma);

        

	// update value of response form field
	response_field = document.getElementById("response");
	response_field.value = response_str;
}