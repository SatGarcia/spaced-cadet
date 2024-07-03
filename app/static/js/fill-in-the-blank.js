

/** Updates the hidden response field in a Fill In The Blank Question form
 *  based on user input.*/
function Update_FITB_Response_Field() {
    let textbox_num = 1;
    let response_list = [];
    let original_user_input_list = [];
        
    //adding all the textboxes to the repsonse list until they dont exist by ID
    while (document.getElementById(`FITB${textbox_num}`) != null){
        //The exact thing that the user put into the text box
        let originalResponse = document.getElementById(`FITB${textbox_num}`).value;
        original_user_input_list.push(originalResponse);
        let response_msg = JSON.stringify(document.getElementById(`FITB${textbox_num}`).value);
        response_list.push(response_msg);
        textbox_num ++;
    }
	
	// Build the response string based on the order of the items in the
	// list.
	let response_str = "";

    original_user_response_str = "";

	// loop through every textbox in the question
    for (let item of response_list) {
		response_str = response_str + item+",";
	}

    //loop through every user input before it was stringified
    for(let input of original_user_input_list){
        original_user_response_str = original_user_response_str + input+`\0`

    }

    //removing the extra separator at the end
    let lastComma = response_str.length -1;
    response_str = response_str.slice(0, lastComma);

    let orig_user_input_last_comma = original_user_response_str.length - 1;
    original_user_response_str = original_user_response_str.slice(0,orig_user_input_last_comma)

        

	// update value of response form field
	response_field = document.getElementById("response");
	response_field.value = response_str;

    //update value of the users original response form field
    original_user_input_field = document.getElementById("original_user_input");
    original_user_input_field.value = original_user_response_str;

}