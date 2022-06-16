function add_ms_option() {  // just copied and pasted from multiple-choice...need to fix
    let options_list = document.getElementById('ms-options');
    let last_option = options_list.lastElementChild;
    //console.log(last_option);
    let last_option_num = parseInt(last_option.getAttribute('option_num'));

    let new_option = last_option.cloneNode(true);
    let new_option_num = last_option_num + 1;
    new_option.setAttribute('option_num', new_option_num);

    let input_items = new_option.getElementsByTagName("input");

    for (let item of Array.from(input_items)) {
        // Change the ID and name of all inputs in the newly create option // area
        let old_id = item.id;
        let new_id = old_id.replace(`-${last_option_num}-`, `-${new_option_num}-`);
        item.id = new_id;

        let old_name = item.getAttribute('name');
        let new_name = old_name.replace(`-${last_option_num}-`, `-${new_option_num}-`);
        item.setAttribute('name', new_name);

        // clear out values of this item (in case they entered something)
        if (new_name.endsWith("-text")) {
            item.value = '';
        }
        else if (new_name.endsWith("-correct")) {
            item.checked = false;
        }
    }

    let label_items = new_option.getElementsByTagName("label");
    for (let item of label_items) {
        // change the "for" attribute on all the labels
        let old_for = item.getAttribute('for');
        let new_for = old_for.replace(`-${last_option_num}-`, `-${new_option_num}-`);
        item.setAttribute('for', new_for);
    }

    options_list.appendChild(new_option);

}
