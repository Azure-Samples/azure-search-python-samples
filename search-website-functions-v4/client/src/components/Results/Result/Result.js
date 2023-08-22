import React from 'react';
import './Result.css';

export default function Result(props) {
    return(
        <div className="card result">
            <a href={`/details/${props.document.id}`}>
                <h6 className="title-style">{props.document.filename}</h6>
            </a>
            <div className="card-body">
                <p>{props.document.content.substring(0, 500)} ...</p>
            </div>
        </div>
    );
}
