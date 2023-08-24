import React from 'react';
import './Result.css';

export default function Result(props) {

    return (
        // <div className="card result">
        //     <a href={`/details/${props.document.id}`}>
        //         <h6 className="title-style">{props.document.filename}</h6>
        //     </a>
        //     <div className="card-body">
        //         <p>{props.document.content.substring(0, 400)} ...</p>
        //     </div>
        //     <div className='card-footer'>
        //         <p>{props.document.author}</p>
        //     </div>
        // </div>

        <div className="card w-full h-full bg-base-100 shadow-xl" >

            <div className="card-body">
                <h2 className="card-title"> <a href={`/details/${props.document.id}`}>
                    <h6 className="title-style">{props.document.filename}</h6>
                </a></h2>
                <p className='whitespace-pre-line p-4 bg-gray-100 rounded-lg'>{props.document.content.substring(0, 200).trim()} ...</p>
                <div className="card-actions flex justify-between items-center">
                    <div className="badge badge-accent">{props.document.author}</div>
                    <a href={`/details/${props.document.id}`}>
                        <h6 className="btn btn-primary">Leer carta</h6>
                    </a>
                </div>
            </div>
        </div>
    );
}
