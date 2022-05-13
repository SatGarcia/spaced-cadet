export function showSnackbarMessage(message) {
    var x = document.getElementById("snackbar");
    x.innerHTML = message;

    x.classList.add("show");

    // hide after 3 seconds
    setTimeout(() => x.classList.remove("show"), 3000);

    // TODO: handle case when show snackbar is displayed before the
    // previous timer went off
}

export function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}

export async function fetchOrRefresh(url, http_method, refresh_url, config) {
    config = (typeof config !== 'undefined') ? config : {
        method: http_method,
        credentials: 'same-origin',
        headers: {
            'X-CSRF-TOKEN': getCookie('csrf_access_token'),
        },
    };

    let response = await fetch(url, config);

    // Check for expired token and (if necessary) refresh token and
    // send the request again.
    if (response.status == 401) {
        const content = await response.json();
        if ('msg' in content && content.msg === "Token has expired") {
            //console.log("Found expired token. Refreshing...");

            const refresh_response = await fetch(refresh_url);
            if (refresh_response.ok) {
                config.headers['X-CSRF-TOKEN'] = getCookie('csrf_access_token');
                response = await fetch(url, config);
            }
        }
    }

    return response;
}

export function findAndRemove(arr, target_id) {
    const target_index = arr.findIndex(item => item.id === target_id);
    if (target_index != -1) {
        arr.splice(target_index, 1);
        return true;
    }
    else {
        return false;
    }
}
