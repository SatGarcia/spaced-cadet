function update_user_response() {
    let textbox_num = 1;
    let response_list = [];
    while (document.getElementById(`FITB${textbox_num}`) != null){ //adding all the textboxes to the repsonse list until they dont exist by ID
        let FITBResponse = document.getElementById(`FITB${textbox_num}`);
        response_list.push(FITBResponse.value);
        textbox_num ++;
    }
	
	// Build the response string based on the order of the items in the
	// list.
	let response_str = "";

	for (let item of response_list) { // loop through every textbox in the question
		response_str = response_str + item+",";
	}

	response_str = response_str;

	// update value of response form field
	response_field = document.getElementById("response");
	response_field.value = response_str;
}