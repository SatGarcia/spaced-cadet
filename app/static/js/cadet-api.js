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


export async function updateQuestionField(field_name, field_value, question_id) {
    const config = {
        method: 'PATCH',
        credentials: 'same-origin',
        headers: {
            "Content-Type": "application/json",
            'X-CSRF-TOKEN': getCookie('csrf_access_token'),
        },
        body: JSON.stringify({[field_name]: field_value})
    }

    const url = `/api/question/${question_id}`;
    return await fetchOrRefresh(url, 'PATCH', refresh_url, config);
}


export async function deleteQuestion(question_id) {
    const url = `/api/question/${question_id}`;
    return await fetchOrRefresh(url, 'DELETE');
}
