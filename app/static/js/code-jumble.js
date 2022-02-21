function initialize_jumble (used_blocks, trashed_blocks) {
	//used_blocks.classList.add("jumble");
	//trashed_blocks.classList.add("jumble");
	let used_items = used_blocks.getElementsByTagName("li");
	let trashed_items = trashed_blocks.getElementsByTagName("li");
	let arr1 = Array.from(used_items)
	let arr2 = Array.from(trashed_items)
	let items = arr1.concat(arr2);

	//console.log(used_items);
	//console.log(trashed_items);

	let selected = null;

	for (let item of items) {
		//console.log(item);
		//console.log(item.childElementCount);

		item.setAttribute("indent-level", 0);

		if (item.parentNode == used_blocks) {
			// list 1 items will be draggable and indentable
			item.draggable = true;

			item.onclick = () => {
				if (item.getAttribute("indent-level") == 0) {
					item.setAttribute("indent-level", 1);
				}
				else {
					item.setAttribute("indent-level", 0);
				}

				// FIXME: 15 should be based on initial amount of padding
				padding_amount = (item.getAttribute("indent-level") * 20) + 15;

				item.style.paddingLeft = padding_amount + "px";
			};
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
					
					//console.log(used_items);
					//console.log(trashed_items);
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
							//console.log("found selected at " + it);
							current_position = it;
						}
						if (item == list_items[it]) {
							new_position = it;
						}
					}
					//console.log("moving from " + current_position + " to " + new_position);

					if (current_position < new_position) {
						item.parentNode.insertBefore(selected, item.nextSibling);
					}
					else {
						item.parentNode.insertBefore(selected, item);
					}
				}
			}
		};
	}
}
