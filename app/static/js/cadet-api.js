import { getCookie, fetchOrRefresh, authenticatedFetch } from './helpers.js';

const refresh_url = Flask.url_for('auth.refresh_jwts');

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

async function updateField(url, field_name, field_value) {
    const config = {
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({[field_name]: field_value})
    }

    return await authenticatedFetch(url, 'PATCH', config);
}


async function setItemInObject(url, item_id) {
    const config = {
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({'id': item_id})
    };

    const response = await authenticatedFetch(url, 'PUT', config);
    return response.updated;
}


export async function createNewObjective(description, is_public) {
    const url = Flask.url_for('objectives_api');
    const new_objective = {
        'description': description,
        'public': is_public,
    };
    return await postItem(url, new_objective);
}


export async function createNewTopic(text) {
    const url = Flask.url_for('topics_api');
    const new_topic = { 'text': text, };
    return await postItem(url, new_topic);
}


export async function setQuestionObjective(question_id, objective_id) {
    const url = Flask.url_for('question_objective', {"question_id": question_id});
    return await setItemInObject(url, objective_id);
}


/*
 * Removes the learning objective from the question with the given ID. On
 * success, it returns the updated version of the Question.
 */
export async function removeQuestionObjective(question_id) {
    const url = Flask.url_for('question_objective', {"question_id": question_id});
    const response = await authenticatedFetch(url, 'DELETE');
    return response.udpated;
}


export async function updateQuestionField(field_name, field_value, question_id) {
    const url = Flask.url_for('question_api', {"question_id": question_id});
    const response = await updateField(url, field_name, field_value);
    return response.updated;
}

/*
 * Deletes the question with the given ID and returns that deleted question.
 */
export async function deleteQuestion(question_id) {
    const url = Flask.url_for('question_api', {"question_id": question_id});
    const response = await authenticatedFetch(url, 'DELETE');
    return response.deleted;
}

export async function setObjectiveTopic(objective_id, topic_id) {
    const url = Flask.url_for('objective_topic', {"objective_id": objective_id});
    return await setItemInObject(url, topic_id);
}

/*
 * Removes the topic from the objective with the given ID. On success, it
 * returns the updated version of the Objective.
 */
export async function removeObjectiveTopic(objective_id) {
    const url = Flask.url_for('objective_topic', {"objective_id": objective_id});
    const response = await authenticatedFetch(url, 'DELETE');
    return response.updated;
}

export async function updateObjectiveField(field_name, field_value, objective_id) {
    const url = Flask.url_for('objective_api', {"objective_id": objective_id});
    const response = await updateField(url, field_name, field_value);
    return response.updated;
}

export async function deleteObjective(objective_id) {
    const url = Flask.url_for('objective_api', {"objective_id": objective_id});
    const response = await authenticatedFetch(url, 'DELETE');
    return response.deleted;
}

export async function searchObjectives(search_string, topic_search_string="") {
    // TODO: should be able to build url with single call to url_for
    let url = Flask.url_for('objective_search_api') + "?html";

    if (search_string !== "") {
        url = url + "&q=" + encodeURIComponent(search_string);
    }
    if (topic_search_string !== "") {
        url = url + "&topics_q=" + encodeURIComponent(topic_search_string);
    }

    return await fetchOrRefresh(url, 'GET', refresh_url);
}

export async function getObjectivesForTopics(topic_ids) {
    const url = Flask.url_for('objectives_api', {"topics": topic_ids.join()});
    const response = await authenticatedFetch(url);
    return response["learning_objectives"];
}

export async function getQuestionsForObjectives(objective_ids) {
    const url = Flask.url_for('questions_api', {"objectives": objective_ids.join()});
    const response = await authenticatedFetch(url);
    return response.questions;
}

export async function getCourseTextbooks(course_id) {
    const url = Flask.url_for('course_textbooks', {"course_id": course_id});
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

async function updateCollection(url, item_ids) {
    const config = {
        method: 'PATCH',
        credentials: 'same-origin',
        headers: {
            "Content-Type": "application/json",
            'X-CSRF-TOKEN': getCookie('csrf_access_token'),
        },
        body: JSON.stringify({'ids': item_ids})
    };

    return await fetchOrRefresh(url, 'PATCH', refresh_url, config);
}

export async function addCourseTextbook(course_id, textbook_id) {
    const url = Flask.url_for('course_textbooks', {"course_id": course_id});
    return await addToCollection(url, [textbook_id]);
}

export async function getCourseTopics(course_id) {
    const url = Flask.url_for("course_topics", { "course_id": course_id });
    const response = await authenticatedFetch(url);
    return response.topics;
}

export async function addCourseTopic(course_id, topic_id) {
    const url = Flask.url_for("course_topics", { "course_id": course_id });
    return await addToCollection(url, [topic_id]);
}

export async function addCourseTopics(course_id, topic_ids) {
    const url = Flask.url_for("course_topics", { "course_id": course_id });
    return await addToCollection(url, topic_ids);
}

export async function removeCourseTextbook(course_id, textbook_id) {
    const url = Flask.url_for('course_textbook', {"course_id": course_id, "textbook_id": textbook_id});
    return await fetchOrRefresh(url, 'DELETE', refresh_url);
}

export async function removeCourseTopic(course_id, topic_id) {
    const url = Flask.url_for('course_topic', {"course_id": course_id, "topic_id": topic_id});
    return await fetchOrRefresh(url, 'DELETE', refresh_url);
}

export async function searchTextbooks(search_string) {
    const url = Flask.url_for('textbook_search_api', {'q': encodeURIComponent(search_string)});
    return await fetchOrRefresh(url, 'GET', refresh_url);
}

export async function searchTopics(search_string) {
    const url = Flask.url_for('topics_api', {'q': encodeURIComponent(search_string)});
    return await fetchOrRefresh(url, 'GET', refresh_url);
}

export async function asyncCallForAllItems(asyncFunc, items, buildParams, postProcessItem) {
    const failures = [];

    for (const item of items) {
        try {
            const params = buildParams(item);
            const result = await asyncFunc(...params); //CadetApi.setObjectiveTopic(lo.id, topic_id);
            if (typeof postProcess !== undefined) {
                postProcessItem(item, result);
            }
        } catch (e) {
            failures.push(item);
        }
    }

    return failures;
}

export async function getQuestionTypes() {
    const url = Flask.url_for('question_types_api');
    const response = await authenticatedFetch(url);
    return response;
}

export async function setAssessmentTopics(course_id, assessment_id, topic_ids) {
    const url = Flask.url_for("course_assessment_collection", { "course_id": course_id, "assessment_id": assessment_id, "collection_name": "topics" });
    return await updateCollection(url, topic_ids);
}

export async function setAssessmentObjectives(course_id, assessment_id, objective_ids) {
    const url = Flask.url_for("course_assessment_collection", { "course_id": course_id, "assessment_id": assessment_id, "collection_name": "objectives" });
    return await updateCollection(url, objective_ids);
}

export async function setAssessmentQuestions(course_id, assessment_id, question_ids) {
    const url = Flask.url_for("course_assessment_collection", { "course_id": course_id, "assessment_id": assessment_id, "collection_name": "questions" });
    return await updateCollection(url, question_ids);
}
