import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Suggestions from './Suggestions/Suggestions';

import "./SearchBar.css";

export default function SearchBar(props) {

    let [q, setQ] = useState("");
    let [suggestions, setSuggestions] = useState([]);
    let [showSuggestions, setShowSuggestions] = useState(false);



    const onSearchHandler = () => {
        const queryParams = {
            q: q,
            semantic_enabled: props.semantic_enabled, // Add this parameter
        };
        console.log({ queryParams })
        props.postSearchHandler(queryParams);
        setShowSuggestions(false);
    };

    const suggestionClickHandler = (s) => {
        document.getElementById("search-box").value = s;
        setShowSuggestions(false);
        props.postSearchHandler(s);
    }

    const onEnterButton = (event) => {
        if (event.keyCode === 13) {
            onSearchHandler();
        }
    }

    const onChangeHandler = () => {
        var searchTerm = document.getElementById("search-box").value;
        setShowSuggestions(true);
        setQ(searchTerm);

        // use this prop if you want to make the search more reactive
        if (props.searchChangeHandler) {
            props.searchChangeHandler(searchTerm);
        }
    }
    const handleSemanticToggle = () => {
        props.setSemanticEnabled(prevSemanticEnabled => !prevSemanticEnabled);
    };

    useEffect(_ => {
        const timer = setTimeout(() => {
            const body = {
                q: q,
                top: 5,
                suggester: 'sg'
            };

            if (q === '') {
                setSuggestions([]);
            } else {
                axios.post('/api/suggest', body)
                    .then(response => {
                        console.log(JSON.stringify(response.data))
                        setSuggestions(response.data.suggestions);
                    })
                    .catch(error => {
                        console.log(error);
                        setSuggestions([]);
                    });
            }
        }, 300);
        return () => clearTimeout(timer);
    }, [q, props]);

    var suggestionDiv;
    if (showSuggestions) {
        suggestionDiv = (<Suggestions suggestions={suggestions} suggestionClickHandler={(s) => suggestionClickHandler(s)}></Suggestions>);
    } else {
        suggestionDiv = (<div></div>);
    }

    return (
        <div >
            <div className="input-group mt-5" onKeyDown={e => onEnterButton(e)}>
                <div className="suggestions" >
                    <input
                        autoComplete="off" // setting for browsers; not the app
                        type="text"
                        id="search-box"
                        className="input input-bordered w-full"
                        placeholder="Buscar cartas"
                        onChange={onChangeHandler}
                        // defaultValue={props.q}
                        onBlur={() => setShowSuggestions(false)}
                        onClick={() => setShowSuggestions(true)}>
                    </input>
                    {suggestionDiv}
                </div>
                <div className="input-group-btn">
                    <button className="btn btn-neutral rounded-0" type="submit" onClick={onSearchHandler}>
                        Buscar
                    </button>
                </div>
            </div>
            <div className="flex flex-row mt-2">
                <label className="label cursor-pointer gap-3">

                    <input
                        type="checkbox"
                        checked={props.semanticEnabled}
                        onChange={handleSemanticToggle}
                        className='checkbox'
                    />
                    <span className="label-text">Semantic Search</span>

                </label>
            </div>
        </div>
    );
};