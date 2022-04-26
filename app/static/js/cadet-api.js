import { getCookie, fetchOrRefresh } from './helpers.js';

const refresh_url = "/auth/refresh";

export async function createNewObjective(description, is_public) {
    const url = "/api/objectives";  // "{{ url_for('objectives_api') }}";

    const message_body = {
        'description': description,
        'public': is_public,
    }

    const config = {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
            "Content-Type": "application/json",
            'X-CSRF-TOKEN': getCookie('csrf_access_token'),
        },
        body: JSON.stringify(message_body),
    };

    return await fetchOrRefresh(url, 'POST', refresh_url, config);
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

export async function createNewTopic(text) {
    const url = "/api/topics";  // "{{ url_for('topics_api') }}";

    const message_body = {
        'text': text,
    }

    const config = {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
            "Content-Type": "application/json",
            'X-CSRF-TOKEN': getCookie('csrf_access_token'),
        },
        body: JSON.stringify(message_body),
    };

    return await fetchOrRefresh(url, 'POST', refresh_url, config);
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

