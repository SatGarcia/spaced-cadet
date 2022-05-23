import { getCookie, fetchOrRefresh } from './helpers.js';

const refresh_url = "/auth/refresh";

export async function postItem(url, item) {
    const config = {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
            "Content-Type": "application/json",
            'X-CSRF-TOKEN': getCookie('csrf_access_token'),
        },
        body: JSON.stringify(item),
    };

    return await fetchOrRefresh(url, 'POST', refresh_url, config);
}

export async function createNewObjective(description, is_public) {
    const url = "/api/objectives";  // "{{ url_for('objectives_api') }}";

    const new_objective = {
        'description': description,
        'public': is_public,
    };

    return await postItem(url, new_objective);
}


export async function createNewTopic(text) {
    const url = "/api/topics";  // "{{ url_for('topics_api') }}";

    const new_topic = {
        'text': text,
    };

    return await postItem(url, new_topic);
}


export async function setQuestionObjective(question_id, objective_id) {
    const url = `/api/question/${question_id}/objective`;
    // FIXME: "{{ url_for('question_objective', question_id=question.id) }}";
    
    const config = {
        method: 'PUT',
        credentials: 'same-origin',
        headers: {
            "Content-Type": "application/json",
            'X-CSRF-TOKEN': getCookie('csrf_access_token'),
        },
        body: JSON.stringify({'id': objective_id})
    };

    return await fetchOrRefresh(url, 'PUT', refresh_url, config);
}


export async function removeQuestionObjective(question_id) {
    const url = `/api/question/${question_id}/objective`;
    return await fetchOrRefresh(url, 'DELETE', refresh_url);
}


async function updateField(model, field_name, field_value, id) {
    const config = {
        method: 'PATCH',
        credentials: 'same-origin',
        headers: {
            "Content-Type": "application/json",
            'X-CSRF-TOKEN': getCookie('csrf_access_token'),
        },
        body: JSON.stringify({[field_name]: field_value})
    }

    const url = `/api/${model}/${id}`;
    return await fetchOrRefresh(url, 'PATCH', refresh_url, config);
}

export async function updateQuestionField(field_name, field_value, question_id) {
    return await updateField('question', field_name, field_value, question_id);
}

export async function deleteQuestion(question_id) {
    const url = `/api/question/${question_id}`;
    return await fetchOrRefresh(url, 'DELETE');
}

export async function setObjectiveTopic(objective_id, topic_id) {
    // TODO: remove code duplication between this and setQuestionObjective
    const url = `/api/objective/${objective_id}/topic`;
    // FIXME: "{{ url_for('objective_topic', objective_id=objective.id) }}";
    
    const config = {
        method: 'PUT',
        credentials: 'same-origin',
        headers: {
            "Content-Type": "application/json",
            'X-CSRF-TOKEN': getCookie('csrf_access_token'),
        },
        body: JSON.stringify({'id': topic_id})
    };

    return await fetchOrRefresh(url, 'PUT', refresh_url, config);
}


export async function removeObjectiveTopic(objective_id) {
    const url = `/api/objective/${objective_id}/topic`;
    return await fetchOrRefresh(url, 'DELETE', refresh_url);
}

export async function updateObjectiveField(field_name, field_value, objective_id) {
    return await updateField('objective', field_name, field_value, objective_id);
}

export async function deleteObjective(objective_id) {
    const url = `/api/objective/${objective_id}`;
    return await fetchOrRefresh(url, 'DELETE');
}

export async function searchObjectives(search_string, topic_search_string="") {
    let url = "/api/objectives/search?html";  // FIXME "{{ url_for('objective_search_api') }}";

    if (search_string !== "") {
        url = url + "&q=" + encodeURIComponent(search_string);
    }
    if (topic_search_string !== "") {
        url = url + "&topics_q=" + encodeURIComponent(topic_search_string);
    }

    return await fetchOrRefresh(url, 'GET', refresh_url);
}

export async function getCourseTextbooks(course_id) {
    const url = `/api/course/${course_id}/textbooks`; // FIXME: url_for
    return await fetchOrRefresh(url, 'GET', refresh_url);
}

async function addToCollection(url, item_ids) {
    const config = {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
            "Content-Type": "application/json",
            'X-CSRF-TOKEN': getCookie('csrf_access_token'),
        },
        body: JSON.stringify({'ids': item_ids})
    };

    return await fetchOrRefresh(url, 'PUT', refresh_url, config);
}

export async function addCourseTextbook(course_id, textbook_id) {
    const url = `/api/course/${course_id}/textbooks`; // FIXME: url_for
    return await addToCollection(url, [textbook_id]);
}

export async function addCourseTopic(course_id, topic_id) {
    const url = `/api/course/${course_id}/topics`; // FIXME: url_for
    return await addToCollection(url, [topic_id]);
}

export async function addCourseTopics(course_id, topic_ids) {
    const url = `/api/course/${course_id}/topics`; // FIXME: url_for
    return await addToCollection(url, topic_ids);
}

export async function removeCourseTextbook(course_id, textbook_id) {
    const url = `/api/course/${course_id}/textbook/${textbook_id}`; // FIXME: url_for
    return await fetchOrRefresh(url, 'DELETE', refresh_url);
}

export async function removeCourseTopic(course_id, topic_id) {
    const url = `/api/course/${course_id}/topic/${topic_id}`; // FIXME: url_for
    return await fetchOrRefresh(url, 'DELETE', refresh_url);
}

export async function searchTextbooks(search_string) {
    let url = "/api/textbooks/search";  // FIXME "{{ url_for('textbook_search_api') }}";
    url = url + "?q=" + encodeURIComponent(search_string);
    return await fetchOrRefresh(url, 'GET', refresh_url);
}

export async function searchTopics(search_string) {
    let url = "/api/topics";  // FIXME: url_for
    url = url + "?q=" + encodeURIComponent(search_string);
    return await fetchOrRefresh(url, 'GET', refresh_url);
}
