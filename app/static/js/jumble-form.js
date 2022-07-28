function add_jumble_block() {
    let blocks_list = document.getElementById('jumble-blocks');
    let last_block = blocks_list.lastElementChild;
    //console.log(last_block);
    let last_block_num = parseInt(last_block.getAttribute('block_num'));

    let new_block = last_block.cloneNode(true);
    let new_block_num = last_block_num + 1;
    new_block.setAttribute('block_num', new_block_num);

    let input_items = new_block.getElementsByTagName("input");
    let textarea_items = new_block.getElementsByTagName("textarea");
    let all_items = Array.from(input_items).concat(Array.from(textarea_items));

    for (let item of all_items) {
        // Change the ID and name of all inputs and text areas in the newly
        // created code block form
        let old_id = item.id;
        let new_id = old_id.replace(`-${last_block_num}-`, `-${new_block_num}-`);
        item.id = new_id;

        let old_name = item.getAttribute('name');
        let new_name = old_name.replace(`-${last_block_num}-`, `-${new_block_num}-`);
        item.setAttribute('name', new_name);

        // clear out values of this item (in case they entered something)
		if (new_name.endsWith("-code")) {
            item.value = '';
        }
		else if (new_name.endsWith("-correct_index") || new_name.endsWith("-correct_indent")) {
        	item.value = '0';
		}
    }

    let label_items = new_block.getElementsByTagName("label");
    for (let item of label_items) {
        // change the "for" attribute on all the labels
        let old_for = item.getAttribute('for');
        let new_for = old_for.replace(`-${last_block_num}-`, `-${new_block_num}-`);
        item.setAttribute('for', new_for);
    }

    blocks_list.appendChild(new_block);

}

function remove_jumble_block() {
    let blocks_list = document.getElementById('jumble-blocks');
    
    let last_block = blocks_list.lastElementChild;
    //console.log(last_block);
    if (last_block !== blocks_list.firstElementChild) {
        blocks_list.removeChild(last_block);
    }

}