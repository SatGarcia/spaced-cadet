function change_indent(block_id, amount) {
	let block_li = document.querySelector(`[block-id="${block_id}"]`);
	console.log(block_li);

	let old_indent = parseInt(block_li.getAttribute("indent-level"));
	let new_indent = old_indent + amount;
	console.log("new_indent: " + new_indent);

	// max indent is 4 so don't do anything if we are at that level
	if (new_indent >= 0 && new_indent <= 4) {
		block_li.setAttribute("indent-level", new_indent);

		// FIXME: 15 should be based on initial amount of padding
		padding_amount = (new_indent * 20) + 15;

		block_li.style.paddingLeft = padding_amount + "px";

		update_response();
	}
}

function update_response() {
	let jumble_list = document.getElementById("jumbley");
	let ordered_items = jumble_list.getElementsByTagName("li");


	// Build the response string based on the order of the items in the
	// jumbley list.
	let response_str = "[";

	for (let item of ordered_items) {
		let block_id = item.getAttribute("block-id");
		let indent_level = item.getAttribute("indent-level");
		let item_str = `(${block_id}, ${indent_level}), `;
		response_str = response_str + item_str;
	}

	response_str = response_str + "]";

	// update value of response form field
	response_field = document.getElementById("response");
	response_field.value = response_str;
}

function initialize_jumble (used_blocks, trashed_blocks) {
	let used_items = used_blocks.getElementsByTagName("li");
	let trashed_items = trashed_blocks.getElementsByTagName("li");
	let arr1 = Array.from(used_items)
	let arr2 = Array.from(trashed_items)
	let items = arr1.concat(arr2);

	//console.log(used_items);
	//console.log(trashed_items);

	let selected = null;

	for (let item of items) {
		item.setAttribute("indent-level", 0);

		if (item.parentNode == used_blocks) {
			// list 1 items will be draggable and indentable
			item.draggable = true;
		}

		// (B2) DRAG START - YELLOW HIGHLIGHT DROPZONES
		item.ondragstart = (ev) => {
			selected = item;
			for (let it of items) {
				if (it != selected) { it.classList.add("hint"); }
			}
		};

		// (B3) DRAG ENTER - RED HIGHLIGHT DROPZONE
		item.ondragenter = (ev) => {
			if (item != selected) { item.classList.add("active"); }
		};

		// (B4) DRAG LEAVE - REMOVE RED HIGHLIGHT
		item.ondragleave = () => {
			item.classList.remove("active");
		};

		// (B5) DRAG END - REMOVE ALL HIGHLIGHTS
		item.ondragend = () => { for (let it of items) {
			it.classList.remove("hint");
			it.classList.remove("active");
		}};

		// (B6) DRAG OVER - PREVENT THE DEFAULT "DROP", SO WE CAN DO OUR OWN
		item.ondragover = (evt) => { evt.preventDefault(); };

		// (B7) ON DROP - DO SOMETHING
		item.ondrop = (evt) => {
			evt.preventDefault();

			// If we drop it in the original place, there is nothing to do
			if (item != selected) {

				// if we're dragging this from the other list, insert it
				// before this item
				if (item.parentNode != selected.parentNode) {
					item.parentNode.insertBefore(selected, item);
				}
				else {
					// they are in the same list, so where to insert depends
					// on their initial relative positions.

					let list_items = null;
					
					if (selected.parentNode == used_blocks) {
						list_items = used_items;
					}
					else {
						list_items = trashed_items;
					}

					let current_position = 0, new_position = 0;

					// Look for the current and new position for the item
					for (let it = 0; it < list_items.length; it++) {
						if (selected == list_items[it]) {
							current_position = it;
						}
						if (item == list_items[it]) {
							new_position = it;
						}
					}

					if (current_position < new_position) {
						item.parentNode.insertBefore(selected, item.nextSibling);
					}
					else {
						item.parentNode.insertBefore(selected, item);
					}
				}

				update_response();
			}
		};
	}
}
